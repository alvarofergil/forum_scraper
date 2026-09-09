"""Discovery orchestration for bootstrap and future incremental runs."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.config import AppConfig
from app.models import (
    CandidateStatus,
    EventType,
    ListingType,
    ParsedTopic,
    TopicListing,
    WatchItem,
    utc_now,
)
from classification.base import ClassificationResult, ListingClassifier
from discovery.matcher import match_listing
from events.service import EventService
from favorites.service import FavoriteService
from sources.armas_es.client import ArmasEsClient
from sources.armas_es.listing_parser import ParsedListingPage, parse_listing_page
from sources.base import TopicFetcher
from storage.database import session_scope
from storage.orm import FavoriteORM
from storage.repositories import (
    AppStateRepository,
    CandidateMatchRepository,
    TopicRepository,
)

BOOTSTRAP_COMPLETED_AT_KEY = "bootstrap_completed_at"
LAST_SUCCESSFUL_DISCOVERY_AT_KEY = "last_successful_discovery_at"
LAST_SUCCESSFUL_FAVORITES_CHECK_AT_KEY = "last_successful_favorites_check_at"
DEFAULT_LISTING_PAGE_SIZE = 18
DEFAULT_PENDING_CANDIDATE_BATCH_SIZE = 50
LOGGER = logging.getLogger(__name__)


class BootstrapAlreadyCompletedError(RuntimeError):
    """Raised when bootstrap is requested more than once without force."""


ListingParser = Callable[..., ParsedListingPage]


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    """Summary of one bootstrap pass."""

    pages_seen: int
    topics_seen: int
    candidates_seen: int
    pending_candidates: int
    classified_candidates: int
    discarded_candidates: int
    favorites_created: int


@dataclass(frozen=True, slots=True)
class RunResult:
    """Summary of one incremental run."""

    discovery_pages_seen: int
    discovery_topics_seen: int
    discovery_candidates_seen: int
    discovery_completed: bool
    discovery_limit_reached: bool
    pending_candidates_checked: int
    pending_candidates_classified: int
    pending_candidates_discarded: int
    pending_candidates_failed: int
    pending_candidates_remaining: int
    pending_candidates_completed: bool
    pending_candidates_skipped: bool
    favorites_checked: int
    favorites_changed: int
    favorites_check_errors: int
    favorites_check_completed: bool
    favorites_check_skipped: bool


class DiscoveryService:
    """Coordinate cheap discovery, candidate classification, and favorite creation."""

    def __init__(
        self,
        *,
        config: AppConfig,
        session_factory: sessionmaker[Session],
        listing_client: ArmasEsClient,
        topic_fetcher: TopicFetcher,
        classifier: ListingClassifier | None = None,
        listing_parser: ListingParser = parse_listing_page,
    ) -> None:
        self.config = config
        self.session_factory = session_factory
        self.listing_client = listing_client
        self.topic_fetcher = topic_fetcher
        self.classifier = classifier
        self.listing_parser = listing_parser

    def bootstrap(self, *, force: bool = False) -> BootstrapResult:
        """Run the bounded initial discovery pass once unless forced."""

        with session_scope(self.session_factory) as session:
            state = AppStateRepository(session)
            if state.get(BOOTSTRAP_COMPLETED_AT_KEY) is not None and not force:
                raise BootstrapAlreadyCompletedError("bootstrap already completed; use --force")

            counters = _BootstrapCounters()
            current_start = 0
            for _page_number in range(self.config.bootstrap.pages):
                response = self.listing_client.get_listing_page(start=current_start)
                parsed_page = self.listing_parser(
                    response.text,
                    base_url=self.config.source.base_url,
                    forum_id=self.config.source.forum_id,
                    current_start=current_start,
                )
                counters.pages_seen += 1
                counters.topics_seen += len(parsed_page.topics)
                self._process_listings(session, parsed_page.topics, counters)
                current_start = _next_start(parsed_page.next_page_url, current_start)

            state.set(BOOTSTRAP_COMPLETED_AT_KEY, utc_now().isoformat().replace("+00:00", "Z"))
            return counters.to_result()

    def run_once(self) -> RunResult:
        """Run one bounded incremental discovery pass followed by favorites check."""

        started_at = utc_now()
        discovery = self._run_incremental_discovery(started_at)
        pending = self._process_pending_candidates()
        favorites = self._run_favorites_check(started_at)
        return RunResult(
            discovery_pages_seen=discovery.pages_seen,
            discovery_topics_seen=discovery.topics_seen,
            discovery_candidates_seen=discovery.candidates_seen,
            discovery_completed=discovery.completed,
            discovery_limit_reached=discovery.limit_reached,
            pending_candidates_checked=pending.checked,
            pending_candidates_classified=pending.classified,
            pending_candidates_discarded=pending.discarded,
            pending_candidates_failed=pending.failed,
            pending_candidates_remaining=pending.remaining,
            pending_candidates_completed=pending.completed,
            pending_candidates_skipped=pending.skipped,
            favorites_checked=favorites.checked,
            favorites_changed=favorites.changed,
            favorites_check_errors=favorites.errors,
            favorites_check_completed=favorites.completed,
            favorites_check_skipped=favorites.skipped,
        )

    def _run_incremental_discovery(self, started_at: datetime) -> _DiscoveryRunCounters:
        with session_scope(self.session_factory) as session:
            state = AppStateRepository(session)
            previous_checkpoint = _parse_state_datetime(
                state.get(LAST_SUCCESSFUL_DISCOVERY_AT_KEY)
            )
            checkpoint = previous_checkpoint or _parse_state_datetime(
                state.get(BOOTSTRAP_COMPLETED_AT_KEY)
            )
            cutoff = (
                checkpoint - timedelta(minutes=self.config.discovery.overlap_minutes)
                if checkpoint is not None
                else None
            )

            counters = _DiscoveryRunCounters()
            current_start = 0
            for _page_number in range(self.config.discovery.max_pages_per_run):
                response = self.listing_client.get_listing_page(start=current_start)
                parsed_page = self.listing_parser(
                    response.text,
                    base_url=self.config.source.base_url,
                    forum_id=self.config.source.forum_id,
                    current_start=current_start,
                )
                counters.pages_seen += 1
                counters.topics_seen += len(parsed_page.topics)

                fresh_listings = _listings_at_or_after_cutoff(parsed_page.topics, cutoff)
                self._process_listings(session, fresh_listings, counters)
                if _page_reached_cutoff(parsed_page.topics, cutoff):
                    counters.completed = True
                    break
                current_start = _next_start(parsed_page.next_page_url, current_start)
            else:
                counters.limit_reached = True
                counters.completed = False
                _log_warning(
                    "discovery reached max_pages_per_run without cutoff",
                    extra={
                        "current_start": current_start,
                        "max_pages_per_run": self.config.discovery.max_pages_per_run,
                        "checkpoint_exists": checkpoint is not None,
                        "last_successful_discovery_at_exists": previous_checkpoint is not None,
                    },
                )

            if counters.completed:
                state.set(
                    LAST_SUCCESSFUL_DISCOVERY_AT_KEY,
                    started_at.isoformat().replace("+00:00", "Z"),
                )
            return counters

    def _run_favorites_check(self, started_at: datetime) -> _FavoriteCheckResult:
        if not self.config.favorites.check_every_run:
            return _FavoriteCheckResult(
                checked=0,
                changed=0,
                errors=0,
                completed=False,
                skipped=True,
            )

        with session_scope(self.session_factory) as session:
            state = AppStateRepository(session)
            watch_items = {item.id: item for item in self.config.watchlist}
            favorites = session.scalars(
                select(FavoriteORM).where(FavoriteORM.is_active.is_(True))
            ).all()
            if not favorites:
                state.set(
                    LAST_SUCCESSFUL_FAVORITES_CHECK_AT_KEY,
                    started_at.isoformat().replace("+00:00", "Z"),
                )
                return _FavoriteCheckResult(
                    checked=0,
                    changed=0,
                    errors=0,
                    completed=True,
                    skipped=False,
                )

            if self.classifier is None:
                _log_warning(
                    "favorites check incomplete because classifier is unavailable",
                    extra={"active_favorites": len(favorites)},
                )
                return _FavoriteCheckResult(
                    checked=0,
                    changed=0,
                    errors=0,
                    completed=False,
                    skipped=False,
                )

            service = FavoriteService(
                session,
                topic_fetcher=self.topic_fetcher,
                classifier=self.classifier,
                config=self.config.favorites,
                ai_config=self.config.ai,
            )
            checked = 0
            changed = 0
            errors = 0
            for favorite in favorites:
                watch_item = watch_items.get(favorite.watch_item_id)
                if watch_item is None:
                    continue
                checked += 1
                if service.check_favorite(favorite.id, watch_item=watch_item):
                    changed += 1
                if service.last_check_had_error:
                    errors += 1

            completed = errors == 0
            if completed:
                state.set(
                    LAST_SUCCESSFUL_FAVORITES_CHECK_AT_KEY,
                    started_at.isoformat().replace("+00:00", "Z"),
                )
            return _FavoriteCheckResult(
                checked=checked,
                changed=changed,
                errors=errors,
                completed=completed,
                skipped=False,
            )

    def _process_pending_candidates(self) -> _PendingCandidateCounters:
        with session_scope(self.session_factory) as session:
            candidates = CandidateMatchRepository(session)
            pending_count = candidates.count_pending()
            counters = _PendingCandidateCounters(remaining=pending_count)
            if pending_count == 0:
                counters.completed = True
                return counters
            if not self.config.ai.enabled:
                counters.skipped = True
                return counters
            if self.classifier is None:
                counters.skipped = True
                return counters

            watch_items = {item.id: item for item in self.config.watchlist}
            favorites = FavoriteService(session, ai_config=self.config.ai)
            events = EventService(session)

            for candidate in candidates.list_pending(limit=DEFAULT_PENDING_CANDIDATE_BATCH_SIZE):
                counters.checked += 1
                topic = candidate.topic
                watch_item = watch_items.get(candidate.watch_item_id)
                if watch_item is None:
                    counters.failed += 1
                    _emit_error(
                        events,
                        topic_external_id=topic.external_topic_id,
                        topic_id=topic.id,
                        watch_item_id=candidate.watch_item_id,
                        scope="pending_candidate_missing_watch_item",
                        error=LookupError("watch item not configured"),
                    )
                    continue

                try:
                    parsed_topic = self.topic_fetcher.fetch_topic(
                        external_topic_id=topic.external_topic_id,
                        canonical_url=topic.canonical_url,
                    )
                    result = self.classifier.classify_new_candidate(watch_item, parsed_topic)
                except Exception as exc:
                    counters.failed += 1
                    _emit_error(
                        events,
                        topic_external_id=topic.external_topic_id,
                        topic_id=topic.id,
                        watch_item_id=watch_item.id,
                        scope="pending_candidate_classification",
                        error=exc,
                    )
                    continue

                if _is_confirmed_offer(result, self.config.ai.match_confidence_threshold):
                    favorite, favorite_created = favorites.create_from_classification(
                        watch_item=watch_item,
                        topic=parsed_topic,
                        result=result,
                        canonical_url=topic.canonical_url,
                    )
                    candidates.mark_classified(candidate, confidence=result.confidence)
                    counters.classified += 1
                    if favorite is not None and favorite_created:
                        counters.favorites_created += 1
                else:
                    candidates.mark_discarded(candidate, confidence=result.confidence)
                    counters.discarded += 1

            session.flush()
            counters.remaining = candidates.count_pending()
            counters.completed = counters.remaining == 0 and counters.failed == 0
            return counters

    def _process_listings(
        self,
        session: Session,
        listings: tuple[TopicListing, ...],
        counters: _BootstrapCounters,
    ) -> None:
        topics = TopicRepository(session)
        candidates = CandidateMatchRepository(session)
        favorites = FavoriteService(session, ai_config=self.config.ai)

        for listing in listings:
            topic_row = topics.upsert_listing(listing)
            session.flush()
            for cheap_match in match_listing(listing, self.config.watchlist):
                counters.candidates_seen += 1
                candidate, created = candidates.get_or_create_pending(
                    topic_id=topic_row.id,
                    watch_item_id=cheap_match.watch_item.id,
                )
                if not created and candidate.status in {
                    CandidateStatus.CLASSIFIED.value,
                    CandidateStatus.DISCARDED.value,
                }:
                    continue
                if not self.config.ai.enabled:
                    if created:
                        counters.pending_candidates += 1
                    continue
                if self.classifier is None:
                    if created:
                        counters.pending_candidates += 1
                    continue

                classified = self._fetch_and_classify(listing, cheap_match.watch_item)
                if classified is None:
                    if created:
                        counters.pending_candidates += 1
                    continue
                parsed_topic, result = classified

                if _is_confirmed_offer(result, self.config.ai.match_confidence_threshold):
                    favorite, favorite_created = favorites.create_from_classification(
                        watch_item=cheap_match.watch_item,
                        topic=parsed_topic,
                        result=result,
                        canonical_url=listing.canonical_url,
                    )
                    candidates.mark_classified(candidate, confidence=result.confidence)
                    counters.classified_candidates += 1
                    if favorite is not None and favorite_created:
                        counters.favorites_created += 1
                else:
                    candidates.mark_discarded(candidate, confidence=result.confidence)
                    counters.discarded_candidates += 1

    def _fetch_and_classify(
        self,
        listing: TopicListing,
        watch_item: WatchItem,
    ) -> tuple[ParsedTopic, ClassificationResult] | None:
        if self.classifier is None:
            raise ValueError("classifier is required to classify candidates")
        try:
            parsed_topic = self.topic_fetcher.fetch_topic(
                external_topic_id=listing.external_topic_id,
                canonical_url=listing.canonical_url,
            )
            result = self.classifier.classify_new_candidate(watch_item, parsed_topic)
        except Exception:
            return None
        return parsed_topic, result


@dataclass(slots=True)
class _BootstrapCounters:
    pages_seen: int = 0
    topics_seen: int = 0
    candidates_seen: int = 0
    pending_candidates: int = 0
    classified_candidates: int = 0
    discarded_candidates: int = 0
    favorites_created: int = 0

    def to_result(self) -> BootstrapResult:
        return BootstrapResult(
            pages_seen=self.pages_seen,
            topics_seen=self.topics_seen,
            candidates_seen=self.candidates_seen,
            pending_candidates=self.pending_candidates,
            classified_candidates=self.classified_candidates,
            discarded_candidates=self.discarded_candidates,
            favorites_created=self.favorites_created,
        )


@dataclass(slots=True)
class _DiscoveryRunCounters(_BootstrapCounters):
    completed: bool = False
    limit_reached: bool = False


@dataclass(slots=True)
class _PendingCandidateCounters:
    checked: int = 0
    classified: int = 0
    discarded: int = 0
    failed: int = 0
    favorites_created: int = 0
    remaining: int = 0
    completed: bool = False
    skipped: bool = False


@dataclass(frozen=True, slots=True)
class _FavoriteCheckResult:
    checked: int
    changed: int
    errors: int
    completed: bool
    skipped: bool


def _emit_error(
    events: EventService,
    *,
    topic_external_id: str,
    topic_id: int | None,
    watch_item_id: str,
    scope: str,
    error: Exception,
) -> None:
    events.emit(
        event_type=EventType.ERROR,
        deduplication_key=(
            f"topic:{topic_external_id}|watch:{watch_item_id}|event:ERROR|"
            f"scope:{scope}|error:{type(error).__name__}"
        ),
        topic_id=topic_id,
        watch_item_id=watch_item_id,
        payload={
            "topic_external_id": topic_external_id,
            "watch_item_id": watch_item_id,
            "scope": scope,
            "error_type": type(error).__name__,
        },
        error_message=_safe_error_message(error),
    )


def _safe_error_message(error: Exception) -> str:
    message = f"{type(error).__name__}: {error}"
    for marker in ("OPENAI_API_KEY", "Authorization", "Cookie", "password", "token"):
        message = message.replace(marker, "[redacted]")
    return message[:1000]


def _log_warning(message: str, *, extra: dict[str, object]) -> None:
    LOGGER.disabled = False
    LOGGER.warning(message, extra=extra)


def _is_confirmed_offer(result: ClassificationResult, threshold: float) -> bool:
    return (
        result.matches_watch_item
        and result.listing_type is ListingType.OFFER
        and result.confidence >= threshold
    )


def _next_start(next_page_url: str | None, current_start: int) -> int:
    if next_page_url is None:
        return current_start + DEFAULT_LISTING_PAGE_SIZE
    values = parse_qs(urlsplit(next_page_url).query).get("start", [])
    if not values:
        return current_start + DEFAULT_LISTING_PAGE_SIZE
    try:
        return int(values[0])
    except ValueError:
        return current_start + DEFAULT_LISTING_PAGE_SIZE


def _parse_state_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _listings_at_or_after_cutoff(
    listings: tuple[TopicListing, ...],
    cutoff: datetime | None,
) -> tuple[TopicListing, ...]:
    if cutoff is None:
        return listings
    return tuple(
        listing
        for listing in listings
        if listing.last_activity_at is None or listing.last_activity_at >= cutoff
    )


def _page_reached_cutoff(
    listings: tuple[TopicListing, ...],
    cutoff: datetime | None,
) -> bool:
    if cutoff is None:
        return not listings
    return any(
        listing.last_activity_at is not None and listing.last_activity_at < cutoff
        for listing in listings
    )
