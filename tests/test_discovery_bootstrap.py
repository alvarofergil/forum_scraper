from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.config import (
    AiConfig,
    AppConfig,
    BootstrapConfig,
    DebugConfig,
    DiscoveryConfig,
    FavoritesConfig,
    NotificationsConfig,
    ScrapingConfig,
    SourceConfig,
)
from app.models import (
    AvailabilityStatus,
    CandidateStatus,
    EventType,
    ListingType,
    ParsedTopic,
    TopicListing,
    TopicPost,
    WatchItem,
)
from classification.base import ClassificationResult
from classification.fake import FakeClassifier
from discovery.service import BootstrapAlreadyCompletedError, DiscoveryService
from sources.armas_es.client import ArmasHttpResponse
from sources.base import TopicFetchTransientError
from storage import create_sqlite_engine, session_factory, session_scope
from storage.orm import CandidateMatchORM, EventORM, FavoriteORM, PriceHistoryORM, TopicORM
from storage.repositories import AppStateRepository


def migrated_db_path(tmp_path: Path) -> Path:
    db_path = tmp_path / "monitor.db"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(config, "head")
    return db_path


class FakeListingClient:
    def __init__(self) -> None:
        self.starts: list[int] = []
        self.error: Exception | None = None

    def get_listing_page(self, *, start: int = 0) -> ArmasHttpResponse:
        self.starts.append(start)
        if self.error is not None:
            raise self.error
        return ArmasHttpResponse(
            status_code=200,
            text=f"listing:{start}",
            final_url="https://example.test",
        )


class FakeTopicFetcher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []
        self.error: Exception | None = None

    def fetch_topic(
        self,
        *,
        external_topic_id: str,
        canonical_url: str | None = None,
    ) -> ParsedTopic:
        self.calls.append((external_topic_id, canonical_url))
        if self.error is not None:
            raise self.error
        return parsed_topic(external_topic_id=external_topic_id)


def watch_item() -> WatchItem:
    return WatchItem(id="watch-001", brand="Acme", model="Target Pro", aliases=("ATP",))


def app_config(
    *,
    pages: int = 10,
    ai_enabled: bool = True,
    favorites_check_every_run: bool = True,
    threshold: float = 0.85,
    overlap_minutes: int = 30,
    max_pages_per_run: int = 50,
) -> AppConfig:
    return AppConfig(
        source=SourceConfig(type="armas_es", base_url="https://www.armas.es", forum_id=96),
        bootstrap=BootstrapConfig(pages=pages),
        discovery=DiscoveryConfig(
            overlap_minutes=overlap_minutes,
            max_pages_per_run=max_pages_per_run,
        ),
        favorites=FavoritesConfig(check_every_run=favorites_check_every_run),
        scraping=ScrapingConfig(request_delay_seconds=0),
        ai=AiConfig(enabled=ai_enabled, match_confidence_threshold=threshold, model="test-model"),
        notifications=NotificationsConfig(),
        debug=DebugConfig(),
        watchlist=(watch_item(),),
    )


def listing(
    external_topic_id: str,
    *,
    title: str = "Vendo Acme Target Pro",
    last_activity_at: datetime | None = None,
) -> TopicListing:
    return TopicListing(
        external_topic_id=external_topic_id,
        canonical_url=f"https://www.armas.es/foros/viewtopic.php?f=96&t={external_topic_id}",
        title=title,
        snippet="Oferta revisada",
        author="seller",
        last_activity_at=last_activity_at,
    )


def parsed_topic(*, external_topic_id: str = "100") -> ParsedTopic:
    return ParsedTopic(
        topic_title="Vendo Acme Target Pro",
        external_topic_id=external_topic_id,
        original_author="seller",
        total_posts=1,
        current_page=1,
        total_pages=1,
        posts=(
            TopicPost(
                sequence_number=1,
                author="seller",
                posted_at=datetime(2026, 1, 2, 10, 30, tzinfo=UTC),
                text="Acme Target Pro por 500 EUR",
                external_post_id=f"post-{external_topic_id}",
            ),
        ),
    )


def positive_result(*, confidence: float = 0.95) -> ClassificationResult:
    return ClassificationResult(
        matches_watch_item=True,
        listing_type=ListingType.OFFER,
        availability=AvailabilityStatus.AVAILABLE,
        price=500,
        currency="EUR",
        confidence=confidence,
    )


def negative_result() -> ClassificationResult:
    return ClassificationResult(
        matches_watch_item=False,
        listing_type=ListingType.OTHER,
        availability=AvailabilityStatus.UNKNOWN,
        confidence=0.2,
    )


def parser_for_pages(pages: dict[int, tuple[TopicListing, ...]]):
    def parse_listing_page(
        html: str,
        *,
        base_url: str,
        forum_id: int,
        current_start: int,
    ):
        from sources.armas_es.listing_parser import ParsedListingPage

        next_url = f"https://www.armas.es/foros/viewforum.php?f=96&start={current_start + 18}"
        return ParsedListingPage(topics=pages.get(current_start, ()), next_page_url=next_url)

    return parse_listing_page


def service_for(
    tmp_path: Path,
    *,
    pages: dict[int, tuple[TopicListing, ...]],
    config: AppConfig | None = None,
    classifier: FakeClassifier | None = None,
) -> tuple[DiscoveryService, FakeListingClient, FakeTopicFetcher]:
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)
    listing_client = FakeListingClient()
    topic_fetcher = FakeTopicFetcher()
    service = DiscoveryService(
        config=config or app_config(),
        session_factory=factory,
        listing_client=listing_client,
        topic_fetcher=topic_fetcher,
        classifier=classifier or FakeClassifier(default_result=positive_result()),
        listing_parser=parser_for_pages(pages),
    )
    return service, listing_client, topic_fetcher


def test_bootstrap_walks_configured_pages(tmp_path: Path) -> None:
    service, listing_client, _topic_fetcher = service_for(
        tmp_path,
        config=app_config(pages=10),
        pages={},
    )

    result = service.bootstrap()

    assert listing_client.starts == [0, 18, 36, 54, 72, 90, 108, 126, 144, 162]
    assert result.pages_seen == 10


def test_bootstrap_opens_only_matched_candidates(tmp_path: Path) -> None:
    service, _listing_client, topic_fetcher = service_for(
        tmp_path,
        pages={
            0: (
                listing("100", title="Vendo Acme Target Pro"),
                listing("200", title="Conversacion general"),
            )
        },
    )

    result = service.bootstrap()

    assert topic_fetcher.calls == [
        ("100", "https://www.armas.es/foros/viewtopic.php?f=96&t=100")
    ]
    assert result.candidates_seen == 1


def test_positive_classification_creates_favorite(tmp_path: Path) -> None:
    service, _listing_client, _topic_fetcher = service_for(
        tmp_path,
        pages={0: (listing("100"),)},
        classifier=FakeClassifier(default_result=positive_result()),
    )

    result = service.bootstrap()

    with session_scope(service.session_factory) as session:
        assert result.favorites_created == 1
        assert session.query(FavoriteORM).count() == 1
        assert session.query(PriceHistoryORM).count() == 1


def test_negative_classification_does_not_create_favorite(tmp_path: Path) -> None:
    service, _listing_client, _topic_fetcher = service_for(
        tmp_path,
        pages={0: (listing("100"),)},
        classifier=FakeClassifier(default_result=negative_result()),
    )

    result = service.bootstrap()

    with session_scope(service.session_factory) as session:
        assert result.favorites_created == 0
        assert session.query(FavoriteORM).count() == 0
        assert session.query(CandidateMatchORM).one().status == "DISCARDED"


def test_ai_disabled_stores_pending_candidate_without_opening_topic(tmp_path: Path) -> None:
    classifier = FakeClassifier(default_result=positive_result())
    service, _listing_client, topic_fetcher = service_for(
        tmp_path,
        config=app_config(ai_enabled=False),
        pages={0: (listing("100"),)},
        classifier=classifier,
    )

    result = service.bootstrap()

    with session_scope(service.session_factory) as session:
        assert topic_fetcher.calls == []
        assert classifier.new_candidate_calls == ()
        assert result.pending_candidates == 1
        assert session.query(CandidateMatchORM).one().status == "PENDING"
        assert session.query(FavoriteORM).count() == 0


def test_bootstrap_rejects_second_run_without_force(tmp_path: Path) -> None:
    service, _listing_client, _topic_fetcher = service_for(tmp_path, pages={})

    service.bootstrap()

    with pytest.raises(BootstrapAlreadyCompletedError):
        service.bootstrap()


def test_force_allows_new_pass_without_deleting_history(tmp_path: Path) -> None:
    service, _listing_client, _topic_fetcher = service_for(
        tmp_path,
        pages={0: (listing("100"),)},
        classifier=FakeClassifier(default_result=positive_result()),
    )

    service.bootstrap()
    result = service.bootstrap(force=True)

    with session_scope(service.session_factory) as session:
        assert result.topics_seen == 1
        assert session.query(FavoriteORM).count() == 1
        assert session.query(PriceHistoryORM).count() == 1
        assert session.query(TopicORM).count() == 1
        assert AppStateRepository(session).get("bootstrap_completed_at") is not None


def test_run_uses_overlap_and_stops_after_cutoff(tmp_path: Path) -> None:
    service, listing_client, _topic_fetcher = service_for(
        tmp_path,
        config=app_config(overlap_minutes=30),
        pages={
            0: (
                listing(
                    "100",
                    last_activity_at=datetime(2026, 1, 2, 11, 45, tzinfo=UTC),
                ),
            ),
            18: (
                listing(
                    "200",
                    last_activity_at=datetime(2026, 1, 2, 11, 20, tzinfo=UTC),
                ),
            ),
        },
    )
    previous_checkpoint = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)

    with session_scope(service.session_factory) as session:
        AppStateRepository(session).set(
            "last_successful_discovery_at",
            previous_checkpoint.isoformat().replace("+00:00", "Z"),
        )

    result = service.run_once()

    with session_scope(service.session_factory) as session:
        assert listing_client.starts == [0, 18]
        assert result.discovery_completed is True
        assert result.discovery_topics_seen == 2
        assert session.query(FavoriteORM).count() == 1
        assert session.query(TopicORM).filter_by(external_topic_id="200").count() == 0
        assert (
            AppStateRepository(session).get("last_successful_discovery_at")
            != previous_checkpoint.isoformat().replace("+00:00", "Z")
        )


def test_run_safety_limit_prevents_false_discovery_checkpoint(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    service, listing_client, _topic_fetcher = service_for(
        tmp_path,
        config=app_config(max_pages_per_run=2),
        pages={
            0: (listing("100", last_activity_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC)),),
            18: (listing("200", last_activity_at=datetime(2026, 1, 2, 11, 59, tzinfo=UTC)),),
        },
    )
    caplog.set_level(logging.WARNING, logger="discovery.service")
    logging.getLogger("discovery.service").addHandler(caplog.handler)
    previous_checkpoint = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)

    with session_scope(service.session_factory) as session:
        AppStateRepository(session).set(
            "last_successful_discovery_at",
            previous_checkpoint.isoformat().replace("+00:00", "Z"),
        )

    result = service.run_once()

    with session_scope(service.session_factory) as session:
        assert listing_client.starts == [0, 18]
        assert result.discovery_completed is False
        assert result.discovery_limit_reached is True
        assert "discovery reached max_pages_per_run without cutoff" in caplog.text
        assert (
            AppStateRepository(session).get("last_successful_discovery_at")
            == previous_checkpoint.isoformat().replace("+00:00", "Z")
        )


def test_run_without_discovery_checkpoint_uses_bootstrap_checkpoint(tmp_path: Path) -> None:
    service, listing_client, _topic_fetcher = service_for(
        tmp_path,
        config=app_config(max_pages_per_run=2, overlap_minutes=30),
        pages={
            0: (
                listing("100", last_activity_at=datetime(2026, 1, 2, 11, 20, tzinfo=UTC)),
            ),
            18: (
                listing("200", last_activity_at=datetime(2026, 1, 2, 11, 10, tzinfo=UTC)),
            ),
        },
    )

    with session_scope(service.session_factory) as session:
        AppStateRepository(session).set(
            "bootstrap_completed_at",
            datetime(2026, 1, 2, 12, 0, tzinfo=UTC).isoformat().replace("+00:00", "Z"),
        )

    result = service.run_once()

    with session_scope(service.session_factory) as session:
        assert listing_client.starts == [0]
        assert result.discovery_completed is True
        assert result.discovery_limit_reached is False
        assert session.query(TopicORM).filter_by(external_topic_id="100").count() == 0
        assert AppStateRepository(session).get("last_successful_discovery_at") is not None


def test_run_does_not_fetch_complete_topic_for_non_candidate_listing(tmp_path: Path) -> None:
    service, _listing_client, topic_fetcher = service_for(
        tmp_path,
        config=app_config(max_pages_per_run=1),
        pages={
            0: (
                listing(
                    "100",
                    title="Conversacion general",
                    last_activity_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
                ),
            )
        },
    )

    service.run_once()

    assert topic_fetcher.calls == []


def test_run_checks_old_favorite_even_when_absent_from_listing(tmp_path: Path) -> None:
    service, _listing_client, topic_fetcher = service_for(
        tmp_path,
        config=app_config(max_pages_per_run=1),
        pages={0: (listing("100"),)},
        classifier=FakeClassifier(default_result=positive_result()),
    )
    service.bootstrap(force=True)
    service.listing_parser = parser_for_pages({})
    topic_fetcher.calls.clear()

    result = service.run_once()

    with session_scope(service.session_factory) as session:
        assert result.favorites_checked == 1
        assert topic_fetcher.calls == [
            ("100", "https://www.armas.es/foros/viewtopic.php?f=96&t=100")
        ]
        assert AppStateRepository(session).get("last_successful_favorites_check_at") is not None


def test_run_skips_favorites_when_disabled_by_config(tmp_path: Path) -> None:
    service, _listing_client, topic_fetcher = service_for(
        tmp_path,
        config=app_config(max_pages_per_run=1, favorites_check_every_run=False),
        pages={0: (listing("100"),)},
        classifier=FakeClassifier(default_result=positive_result()),
    )
    service.bootstrap(force=True)
    service.listing_parser = parser_for_pages({})
    topic_fetcher.calls.clear()

    result = service.run_once()

    with session_scope(service.session_factory) as session:
        assert result.favorites_checked == 0
        assert result.favorites_changed == 0
        assert result.favorites_check_completed is False
        assert result.favorites_check_skipped is True
        assert topic_fetcher.calls == []
        assert AppStateRepository(session).get("last_successful_favorites_check_at") is None


def test_run_with_active_favorite_and_no_classifier_checks_unchanged_topic(
    tmp_path: Path,
) -> None:
    service, _listing_client, topic_fetcher = service_for(
        tmp_path,
        config=app_config(max_pages_per_run=1),
        pages={0: (listing("100"),)},
        classifier=FakeClassifier(default_result=positive_result()),
    )
    service.bootstrap(force=True)
    service.classifier = None
    service.listing_parser = parser_for_pages({})
    topic_fetcher.calls.clear()

    result = service.run_once()

    with session_scope(service.session_factory) as session:
        assert result.favorites_checked == 1
        assert result.favorites_unchanged == 1
        assert result.favorites_changed == 0
        assert result.favorites_changed_unclassified == 0
        assert result.favorites_check_completed is True
        assert result.favorites_check_skipped is False
        assert topic_fetcher.calls == [
            ("100", "https://www.armas.es/foros/viewtopic.php?f=96&t=100")
        ]
        assert AppStateRepository(session).get("last_successful_favorites_check_at") is not None


def test_run_without_active_favorites_completes_check_without_fetching(tmp_path: Path) -> None:
    service, _listing_client, topic_fetcher = service_for(
        tmp_path,
        config=app_config(max_pages_per_run=1),
        pages={},
    )

    result = service.run_once()

    with session_scope(service.session_factory) as session:
        assert result.favorites_checked == 0
        assert result.favorites_changed == 0
        assert result.favorites_check_completed is True
        assert result.favorites_check_skipped is False
        assert topic_fetcher.calls == []
        assert AppStateRepository(session).get("last_successful_favorites_check_at") is not None


def test_run_listing_failure_still_processes_pending_and_favorites(
    tmp_path: Path,
) -> None:
    service, listing_client, topic_fetcher = service_for(
        tmp_path,
        config=app_config(max_pages_per_run=1, ai_enabled=False),
        pages={0: (listing("100"),)},
        classifier=FakeClassifier(default_result=positive_result()),
    )
    service.run_once()
    service.config = app_config(max_pages_per_run=1, ai_enabled=True)
    service.classifier = FakeClassifier(default_result=positive_result())
    listing_client.error = RuntimeError("listing failed Authorization: Bearer abc")
    topic_fetcher.calls.clear()

    result = service.run_once()

    with session_scope(service.session_factory) as session:
        assert result.discovery_completed is False
        assert result.pending_candidates_checked == 1
        assert result.pending_candidates_classified == 1
        assert result.favorites_checked == 1
        assert result.favorites_unchanged == 1
        assert topic_fetcher.calls == [
            ("100", "https://www.armas.es/foros/viewtopic.php?f=96&t=100"),
            ("100", "https://www.armas.es/foros/viewtopic.php?f=96&t=100"),
        ]
        errors = session.query(EventORM).filter_by(event_type=EventType.ERROR.value).all()
        assert len(errors) == 1
        assert "Authorization" not in errors[0].error_message
        assert "abc" not in errors[0].error_message


def test_newly_failed_candidate_is_not_retried_twice_in_same_run(tmp_path: Path) -> None:
    service, _listing_client, topic_fetcher = service_for(
        tmp_path,
        config=app_config(max_pages_per_run=1),
        pages={0: (listing("100"),)},
        classifier=FakeClassifier(default_result=positive_result()),
    )
    topic_fetcher.error = TopicFetchTransientError("temporary failure")

    first = service.run_once()
    second = service.run_once()

    with session_scope(service.session_factory) as session:
        assert first.discovery_candidates_seen == 1
        assert first.pending_candidates_checked == 0
        assert first.pending_candidates_remaining == 1
        assert second.pending_candidates_checked == 0
        assert len(topic_fetcher.calls) == 2
        assert session.query(CandidateMatchORM).one().status == CandidateStatus.PENDING.value


def test_empty_listing_with_checkpoint_does_not_spin_to_max_pages(tmp_path: Path) -> None:
    service, listing_client, _topic_fetcher = service_for(
        tmp_path,
        config=app_config(max_pages_per_run=5),
        pages={},
    )
    with session_scope(service.session_factory) as session:
        AppStateRepository(session).set(
            "last_successful_discovery_at",
            datetime(2026, 1, 2, 12, 0, tzinfo=UTC).isoformat().replace("+00:00", "Z"),
        )

    result = service.run_once()

    assert listing_client.starts == [0]
    assert result.discovery_completed is True
    assert result.discovery_limit_reached is False


def test_run_retries_existing_pending_candidate(tmp_path: Path) -> None:
    classifier = FakeClassifier(default_result=positive_result())
    service, _listing_client, topic_fetcher = service_for(
        tmp_path,
        config=app_config(max_pages_per_run=1, ai_enabled=False),
        pages={0: (listing("100"),)},
        classifier=classifier,
    )
    service.run_once()
    service.config = app_config(max_pages_per_run=1, ai_enabled=True)

    result = service.run_once()

    with session_scope(service.session_factory) as session:
        assert result.discovery_candidates_seen == 1
        assert topic_fetcher.calls[0] == (
            "100",
            "https://www.armas.es/foros/viewtopic.php?f=96&t=100",
        )
        assert topic_fetcher.calls == [
            ("100", "https://www.armas.es/foros/viewtopic.php?f=96&t=100")
        ] * 2
        assert classifier.new_candidate_calls
        assert session.query(CandidateMatchORM).one().status == CandidateStatus.CLASSIFIED.value


def test_run_processes_pending_candidate_absent_from_current_listing(tmp_path: Path) -> None:
    classifier = FakeClassifier(default_result=positive_result())
    service, _listing_client, topic_fetcher = service_for(
        tmp_path,
        config=app_config(max_pages_per_run=1, ai_enabled=False),
        pages={0: (listing("100"),)},
        classifier=classifier,
    )
    service.run_once()
    service.config = app_config(max_pages_per_run=1, ai_enabled=True)
    service.listing_parser = parser_for_pages({})
    topic_fetcher.calls.clear()

    result = service.run_once()

    with session_scope(service.session_factory) as session:
        assert result.pending_candidates_checked == 1
        assert result.pending_candidates_classified == 1
        assert result.pending_candidates_remaining == 0
        assert result.pending_candidates_completed is True
        assert topic_fetcher.calls[0] == (
            "100",
            "https://www.armas.es/foros/viewtopic.php?f=96&t=100",
        )
        assert session.query(CandidateMatchORM).one().status == CandidateStatus.CLASSIFIED.value
        assert session.query(FavoriteORM).count() == 1


def test_pending_positive_candidate_creates_favorite_once(tmp_path: Path) -> None:
    classifier = FakeClassifier(default_result=positive_result())
    service, _listing_client, _topic_fetcher = service_for(
        tmp_path,
        config=app_config(max_pages_per_run=1, ai_enabled=False),
        pages={0: (listing("100"),)},
        classifier=classifier,
    )
    service.run_once()
    service.config = app_config(max_pages_per_run=1, ai_enabled=True)
    service.listing_parser = parser_for_pages({})

    first = service.run_once()
    second = service.run_once()

    with session_scope(service.session_factory) as session:
        assert first.pending_candidates_classified == 1
        assert second.pending_candidates_checked == 0
        assert session.query(FavoriteORM).count() == 1
        assert session.query(CandidateMatchORM).one().status == CandidateStatus.CLASSIFIED.value


def test_pending_negative_candidate_is_discarded(tmp_path: Path) -> None:
    classifier = FakeClassifier(default_result=negative_result())
    service, _listing_client, _topic_fetcher = service_for(
        tmp_path,
        config=app_config(max_pages_per_run=1, ai_enabled=False),
        pages={0: (listing("100"),)},
        classifier=classifier,
    )
    service.run_once()
    service.config = app_config(max_pages_per_run=1, ai_enabled=True)
    service.listing_parser = parser_for_pages({})

    result = service.run_once()

    with session_scope(service.session_factory) as session:
        assert result.pending_candidates_discarded == 1
        assert result.pending_candidates_remaining == 0
        assert session.query(FavoriteORM).count() == 0
        assert session.query(CandidateMatchORM).one().status == CandidateStatus.DISCARDED.value


def test_pending_fetch_error_remains_pending_and_emits_deduplicated_error(
    tmp_path: Path,
) -> None:
    service, _listing_client, topic_fetcher = service_for(
        tmp_path,
        config=app_config(max_pages_per_run=1, ai_enabled=False),
        pages={0: (listing("100"),)},
        classifier=FakeClassifier(default_result=positive_result()),
    )
    service.run_once()
    service.config = app_config(max_pages_per_run=1, ai_enabled=True)
    service.listing_parser = parser_for_pages({})
    topic_fetcher.error = TopicFetchTransientError("temporary OPENAI_API_KEY token")

    first = service.run_once()
    second = service.run_once()

    with session_scope(service.session_factory) as session:
        assert first.pending_candidates_failed == 1
        assert second.pending_candidates_failed == 1
        assert session.query(CandidateMatchORM).one().status == CandidateStatus.PENDING.value
        assert session.query(FavoriteORM).count() == 0
        assert session.query(EventORM).filter_by(event_type=EventType.ERROR.value).count() == 1
        assert "OPENAI_API_KEY" not in session.query(EventORM).one().error_message


def test_pending_classification_error_remains_retryable(tmp_path: Path) -> None:
    classifier = FakeClassifier(error=RuntimeError("classifier unavailable"))
    service, _listing_client, _topic_fetcher = service_for(
        tmp_path,
        config=app_config(max_pages_per_run=1, ai_enabled=False),
        pages={0: (listing("100"),)},
        classifier=classifier,
    )
    service.run_once()
    service.config = app_config(max_pages_per_run=1, ai_enabled=True)
    service.listing_parser = parser_for_pages({})

    result = service.run_once()

    with session_scope(service.session_factory) as session:
        assert result.pending_candidates_failed == 1
        assert result.pending_candidates_remaining == 1
        assert result.pending_candidates_completed is False
        assert session.query(CandidateMatchORM).one().status == CandidateStatus.PENDING.value
        assert session.query(FavoriteORM).count() == 0
        assert session.query(EventORM).filter_by(event_type=EventType.ERROR.value).count() == 1


def test_run_does_not_reclassify_discarded_candidate(tmp_path: Path) -> None:
    classifier = FakeClassifier(default_result=negative_result())
    service, _listing_client, topic_fetcher = service_for(
        tmp_path,
        config=app_config(max_pages_per_run=1),
        pages={0: (listing("100"),)},
        classifier=classifier,
    )
    service.run_once()
    topic_fetcher.calls.clear()

    result = service.run_once()

    assert result.discovery_candidates_seen == 1
    assert topic_fetcher.calls == []
    assert len(classifier.new_candidate_calls) == 1


def test_run_does_not_reclassify_classified_candidate_from_listing(tmp_path: Path) -> None:
    classifier = FakeClassifier(default_result=positive_result())
    service, _listing_client, topic_fetcher = service_for(
        tmp_path,
        config=app_config(max_pages_per_run=1),
        pages={0: (listing("100"),)},
        classifier=classifier,
    )
    service.run_once()
    topic_fetcher.calls.clear()

    result = service.run_once()

    assert result.discovery_candidates_seen == 1
    assert topic_fetcher.calls == [
        ("100", "https://www.armas.es/foros/viewtopic.php?f=96&t=100")
    ]
    assert result.favorites_checked == 1
    assert len(classifier.new_candidate_calls) == 1
    assert len(classifier.favorite_update_calls) == 0


def test_two_runs_without_changes_do_not_duplicate_events(tmp_path: Path) -> None:
    service, _listing_client, _topic_fetcher = service_for(
        tmp_path,
        config=app_config(max_pages_per_run=1),
        pages={0: (listing("100"),)},
        classifier=FakeClassifier(default_result=positive_result()),
    )

    service.run_once()
    service.run_once()

    with session_scope(service.session_factory) as session:
        assert session.query(FavoriteORM).count() == 1
        assert session.query(EventORM).count() == 1
