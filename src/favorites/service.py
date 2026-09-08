"""Favorite monitoring, content hashing, and history updates."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import FavoritesConfig
from app.models import (
    AvailabilityStatus,
    EventType,
    ListingType,
    ParsedTopic,
    TopicPost,
    WatchItem,
    utc_now,
)
from classification.base import ClassificationResult, ListingClassifier, PreviousFavoriteState
from discovery.matcher import normalize_text
from events.service import EventService
from sources.armas_es.client import (
    ArmasEsClient,
    ArmasHttpClientError,
    ArmasTopicNotFoundError,
    ArmasTopicUnavailableError,
)
from sources.armas_es.topic_parser import parse_topic_page
from storage.orm import (
    FavoriteORM,
    PriceHistoryORM,
    StatusHistoryORM,
    TopicORM,
    TopicPostORM,
)


TopicParser = Callable[[str], ParsedTopic]


def post_content_hash(external_topic_id: str, post: TopicPost) -> str:
    """Hash one post using stable cleaned fields, never raw HTML."""

    posted_at = post.posted_at.isoformat().replace("+00:00", "Z")
    parts = (
        external_topic_id,
        post.external_post_id or "",
        post.author,
        posted_at,
        normalize_text(re.sub(r"<[^>]*>", " ", post.text)),
    )
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def compute_content_hash(topic: ParsedTopic) -> str:
    """Hash the visible topic content from stable per-post hashes."""

    title_hash = hashlib.sha256(normalize_text(topic.topic_title).encode("utf-8")).hexdigest()
    post_hashes = [
        post_content_hash(topic.external_topic_id, post)
        for post in sorted(topic.posts, key=lambda item: item.sequence_number)
    ]
    return hashlib.sha256("\n".join([title_hash, *post_hashes]).encode("utf-8")).hexdigest()


class FavoriteService:
    """Create and check favorites without owning discovery or notifications."""

    def __init__(
        self,
        session: Session,
        *,
        client: ArmasEsClient | None = None,
        classifier: ListingClassifier | None = None,
        parser: TopicParser = parse_topic_page,
        config: FavoritesConfig | None = None,
        events: EventService | None = None,
    ) -> None:
        self.session = session
        self.client = client
        self.classifier = classifier
        self.parser = parser
        self.config = config or FavoritesConfig()
        self.events = events or EventService(session)

    def create_from_classification(
        self,
        *,
        watch_item: WatchItem,
        topic: ParsedTopic,
        result: ClassificationResult,
    ) -> tuple[FavoriteORM | None, bool]:
        """Create a favorite when classification confirms a relevant offer."""

        if not _is_positive_offer(result):
            return None, False

        topic_row = self._get_or_create_topic(topic)
        existing = self.session.scalar(select(FavoriteORM).where(FavoriteORM.topic_id == topic_row.id))
        if existing is not None:
            return existing, False

        content_hash = compute_content_hash(topic)
        favorite = FavoriteORM(
            topic_id=topic_row.id,
            watch_item_id=watch_item.id,
            status=result.availability.value,
            current_price=_price_decimal(result.price),
            currency=result.currency,
            price_updated_at=utc_now() if result.price is not None else None,
            is_active=result.availability
            not in {AvailabilityStatus.SOLD, AvailabilityStatus.WITHDRAWN},
            last_checked_at=utc_now(),
            last_content_hash=content_hash,
            last_classified_at=utc_now(),
        )
        self.session.add(favorite)
        self.session.flush()
        self._record_posts(topic_row, topic)
        self._record_price_history(favorite, content_hash)
        self._record_status_history(favorite)
        self.events.emit_for_topic(
            event_type=EventType.NEW_FAVORITE,
            topic_external_id=topic.external_topic_id,
            content_hash=content_hash,
            topic_id=topic_row.id,
            favorite_id=favorite.id,
            watch_item_id=watch_item.id,
            payload={
                "topic_external_id": topic.external_topic_id,
                "watch_item_id": watch_item.id,
                "availability": favorite.status,
                "price": float(favorite.current_price) if favorite.current_price is not None else None,
                "currency": favorite.currency,
            },
        )
        return favorite, True

    def check_favorite(self, favorite_id: int, *, watch_item: WatchItem) -> bool:
        """Fetch and classify a favorite only when its stable content hash changed."""

        favorite = self.session.get(FavoriteORM, favorite_id)
        if favorite is None or favorite.topic is None or not favorite.is_active:
            return False
        if self.client is None or self.classifier is None:
            raise ValueError("client and classifier are required to check favorites")

        try:
            response = self.client.get_topic(favorite.topic.external_topic_id)
        except (ArmasTopicNotFoundError, ArmasTopicUnavailableError):
            return self._record_unavailable_attempt(favorite)
        except ArmasHttpClientError:
            favorite.last_checked_at = utc_now()
            return False

        parsed_topic = self.parser(response.text)
        content_hash = compute_content_hash(parsed_topic)
        favorite.last_checked_at = utc_now()
        favorite.unavailable_confirmation_count = 0
        self._record_posts(favorite.topic, parsed_topic)
        if content_hash == favorite.last_content_hash:
            return False

        previous = PreviousFavoriteState(
            availability=AvailabilityStatus(favorite.status),
            price=float(favorite.current_price) if favorite.current_price is not None else None,
            currency=favorite.currency,
            content_hash=favorite.last_content_hash,
        )
        result = self.classifier.classify_favorite_update(previous, watch_item, parsed_topic)
        self._apply_classification_update(favorite, parsed_topic, result, content_hash)
        return True

    def _get_or_create_topic(self, topic: ParsedTopic) -> TopicORM:
        existing = self.session.scalar(
            select(TopicORM).where(TopicORM.external_topic_id == topic.external_topic_id)
        )
        if existing is not None:
            existing.title = topic.topic_title
            return existing

        row = TopicORM(
            external_topic_id=topic.external_topic_id,
            canonical_url=f"https://www.armas.es/foros/viewtopic.php?f=96&t={topic.external_topic_id}",
            title=topic.topic_title,
            author=topic.original_author,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def _record_posts(self, topic_row: TopicORM, topic: ParsedTopic) -> None:
        existing = {
            post.sequence_number: post
            for post in self.session.scalars(
                select(TopicPostORM).where(TopicPostORM.topic_id == topic_row.id)
            )
        }
        for post in topic.posts:
            content_hash = post_content_hash(topic.external_topic_id, post)
            row = existing.get(post.sequence_number)
            if row is None:
                row = TopicPostORM(
                    topic_id=topic_row.id,
                    sequence_number=post.sequence_number,
                    content_hash=content_hash,
                )
                self.session.add(row)
            row.external_post_id = post.external_post_id
            row.author = post.author
            row.posted_at = post.posted_at
            row.content_hash = content_hash

    def _apply_classification_update(
        self,
        favorite: FavoriteORM,
        topic: ParsedTopic,
        result: ClassificationResult,
        content_hash: str,
    ) -> None:
        previous_price = favorite.current_price
        previous_status = AvailabilityStatus(favorite.status)
        if result.price is not None:
            favorite.current_price = _price_decimal(result.price)
            favorite.currency = result.currency
            if favorite.current_price != previous_price:
                favorite.price_updated_at = utc_now()
                self._record_price_history(favorite, content_hash)
                self.events.emit(
                    event_type=EventType.PRICE_CHANGED,
                    deduplication_key=(
                        f"topic:{topic.external_topic_id}|watch:{favorite.watch_item_id}|"
                        f"event:PRICE_CHANGED|hash:{content_hash}|old:{previous_price}|"
                        f"new:{favorite.current_price}"
                    ),
                    topic_id=favorite.topic_id,
                    favorite_id=favorite.id,
                    watch_item_id=favorite.watch_item_id,
                    payload={
                        "old_price": float(previous_price) if previous_price is not None else None,
                        "new_price": float(favorite.current_price),
                        "currency": favorite.currency,
                    },
                )

        favorite.status = result.availability.value
        if result.availability != previous_status:
            self._record_status_history(favorite)
            self.events.emit(
                event_type=EventType.STATUS_CHANGED,
                deduplication_key=(
                    f"topic:{topic.external_topic_id}|watch:{favorite.watch_item_id}|"
                    f"event:STATUS_CHANGED|hash:{content_hash}|old:{previous_status.value}|"
                    f"new:{favorite.status}"
                ),
                topic_id=favorite.topic_id,
                favorite_id=favorite.id,
                watch_item_id=favorite.watch_item_id,
                payload={"old_status": previous_status.value, "new_status": favorite.status},
            )

        if result.availability in {AvailabilityStatus.SOLD, AvailabilityStatus.WITHDRAWN}:
            favorite.is_active = False
            self.events.emit_for_topic(
                event_type=EventType.BECAME_UNAVAILABLE,
                topic_external_id=topic.external_topic_id,
                content_hash=content_hash,
                topic_id=favorite.topic_id,
                favorite_id=favorite.id,
                watch_item_id=favorite.watch_item_id,
                payload={"availability": favorite.status},
            )

        favorite.last_content_hash = content_hash
        favorite.last_classified_at = utc_now()

    def _record_unavailable_attempt(self, favorite: FavoriteORM) -> bool:
        favorite.last_checked_at = utc_now()
        favorite.unavailable_confirmation_count += 1
        if favorite.unavailable_confirmation_count < self.config.unavailable_confirmation_runs:
            return False
        previous_status = AvailabilityStatus(favorite.status)
        favorite.status = AvailabilityStatus.WITHDRAWN.value
        favorite.is_active = False
        content_hash = f"unavailable:{favorite.unavailable_confirmation_count}"
        self._record_status_history(favorite)
        self.events.emit(
            event_type=EventType.STATUS_CHANGED,
            deduplication_key=(
                f"topic:{favorite.topic.external_topic_id}|watch:{favorite.watch_item_id}|"
                f"event:STATUS_CHANGED|hash:{content_hash}|old:{previous_status.value}|"
                f"new:{favorite.status}"
            ),
            topic_id=favorite.topic_id,
            favorite_id=favorite.id,
            watch_item_id=favorite.watch_item_id,
            payload={"old_status": previous_status.value, "new_status": favorite.status},
        )
        self.events.emit_for_topic(
            event_type=EventType.BECAME_UNAVAILABLE,
            topic_external_id=favorite.topic.external_topic_id,
            content_hash=content_hash,
            topic_id=favorite.topic_id,
            favorite_id=favorite.id,
            watch_item_id=favorite.watch_item_id,
            payload={
                "availability": favorite.status,
                "unavailable_confirmation_count": favorite.unavailable_confirmation_count,
            },
        )
        return True

    def _record_price_history(self, favorite: FavoriteORM, content_hash: str) -> None:
        if favorite.current_price is None:
            return
        self.session.add(
            PriceHistoryORM(
                favorite_id=favorite.id,
                price=favorite.current_price,
                currency=favorite.currency,
                source_hash=content_hash,
            )
        )

    def _record_status_history(self, favorite: FavoriteORM) -> None:
        self.session.add(StatusHistoryORM(favorite_id=favorite.id, status=favorite.status))


def _is_positive_offer(result: ClassificationResult) -> bool:
    return result.matches_watch_item and result.listing_type == ListingType.OFFER


def _price_decimal(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"))
