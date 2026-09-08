from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from alembic.config import Config

from alembic import command
from app.config import AiConfig, FavoritesConfig
from app.models import (
    AvailabilityStatus,
    EventType,
    ListingType,
    ParsedTopic,
    TopicPost,
    WatchItem,
)
from classification.base import ClassificationResult
from classification.fake import FakeClassifier
from favorites.service import FavoriteService, compute_content_hash, post_content_hash
from sources.base import (
    TopicFetchNotFoundError,
    TopicFetchTransientError,
)
from storage import create_sqlite_engine, session_factory, session_scope
from storage.orm import (
    EventORM,
    FavoriteORM,
    PriceHistoryORM,
    StatusHistoryORM,
    TopicPostORM,
)


def migrated_db_path(tmp_path: Path) -> Path:
    db_path = tmp_path / "monitor.db"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(config, "head")
    return db_path


class FakeTopicFetcher:
    def __init__(self, parsed_topic: ParsedTopic | None = None) -> None:
        self.parsed_topic = parsed_topic or topic()
        self.calls: list[str] = []
        self.error: Exception | None = None

    def fetch_topic(
        self,
        *,
        external_topic_id: str,
        canonical_url: str | None = None,
    ) -> ParsedTopic:
        self.calls.append(f"{external_topic_id}|{canonical_url}")
        if self.error is not None:
            raise self.error
        return self.parsed_topic


def watch_item() -> WatchItem:
    return WatchItem(id="item_001", brand="Acme", model="Target Pro")


def canonical_url() -> str:
    return "https://example.test/topics/123"


def topic(
    *,
    title: str = "Vendo Acme Target Pro",
    text: str = "Acme Target Pro por 123 EUR",
    post_id: str = "456",
) -> ParsedTopic:
    return ParsedTopic(
        topic_title=title,
        external_topic_id="123",
        original_author="seller_001",
        total_posts=1,
        current_page=1,
        total_pages=1,
        posts=(
            TopicPost(
                sequence_number=1,
                author="seller_001",
                posted_at=datetime(2026, 1, 2, 10, 30, tzinfo=UTC),
                text=text,
                external_post_id=post_id,
            ),
        ),
    )


def positive_result(
    *,
    price: float | None = 123,
    availability: AvailabilityStatus = AvailabilityStatus.AVAILABLE,
    confidence: float = 0.95,
) -> ClassificationResult:
    return ClassificationResult(
        matches_watch_item=True,
        listing_type=ListingType.OFFER,
        availability=availability,
        price=price,
        currency="EUR" if price is not None else None,
        confidence=confidence,
    )


def test_content_hash_uses_normalized_post_text_not_raw_html() -> None:
    first = topic(text="Acme Target-Pro<br> por 123 EUR")
    second = topic(text=" acme target pro por 123 eur ")

    assert compute_content_hash(first) == compute_content_hash(second)
    assert post_content_hash(first.external_topic_id, first.posts[0]) == post_content_hash(
        second.external_topic_id,
        second.posts[0],
    )


def test_content_hash_changes_when_title_changes() -> None:
    available = topic(title="Vendo Acme Target Pro")
    sold = topic(title="Vendido Acme Target Pro")

    assert compute_content_hash(available) != compute_content_hash(sold)


def test_create_new_favorite_creates_event_and_histories(tmp_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)

    with session_scope(factory) as session:
        service = FavoriteService(session)

        favorite, created = service.create_from_classification(
            watch_item=watch_item(),
            topic=topic(),
            result=positive_result(),
            canonical_url=canonical_url(),
        )

        assert created is True
        assert favorite.watch_item_id == "item_001"
        assert favorite.status == AvailabilityStatus.AVAILABLE.value
        assert str(favorite.current_price) == "123.00"
        assert favorite.last_content_hash == compute_content_hash(topic())
        assert (
            session.query(EventORM).filter_by(event_type=EventType.NEW_FAVORITE.value).count()
            == 1
        )
        assert session.query(PriceHistoryORM).count() == 1
        assert session.query(StatusHistoryORM).count() == 1
        assert session.query(TopicPostORM).count() == 1


def test_create_favorite_is_idempotent_for_same_topic(tmp_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)

    with session_scope(factory) as session:
        service = FavoriteService(session)

        first, first_created = service.create_from_classification(
            watch_item=watch_item(),
            topic=topic(),
            result=positive_result(),
            canonical_url=canonical_url(),
        )
        second, second_created = service.create_from_classification(
            watch_item=watch_item(),
            topic=topic(),
            result=positive_result(),
            canonical_url=canonical_url(),
        )

        assert first.id == second.id
        assert first_created is True
        assert second_created is False
        assert session.query(EventORM).count() == 1


def test_non_offer_or_non_match_does_not_create_favorite(tmp_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)

    with session_scope(factory) as session:
        service = FavoriteService(session)
        result = ClassificationResult(
            matches_watch_item=True,
            listing_type=ListingType.WANTED,
            availability=AvailabilityStatus.UNKNOWN,
            confidence=0.8,
        )

        favorite, created = service.create_from_classification(
            watch_item=watch_item(),
            topic=topic(),
            result=result,
            canonical_url=canonical_url(),
        )

        assert favorite is None
        assert created is False
        assert session.query(FavoriteORM).count() == 0


def test_positive_offer_below_configured_threshold_does_not_create_favorite(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)

    with session_scope(factory) as session:
        service = FavoriteService(
            session,
            ai_config=AiConfig(match_confidence_threshold=0.85),
        )

        favorite, created = service.create_from_classification(
            watch_item=watch_item(),
            topic=topic(),
            result=positive_result(confidence=0.84),
            canonical_url=canonical_url(),
        )

        assert favorite is None
        assert created is False
        assert session.query(FavoriteORM).count() == 0
        assert session.query(EventORM).count() == 0
        assert session.query(PriceHistoryORM).count() == 0
        assert session.query(StatusHistoryORM).count() == 0


def test_positive_offer_at_configured_threshold_creates_favorite(tmp_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)

    with session_scope(factory) as session:
        service = FavoriteService(
            session,
            ai_config=AiConfig(match_confidence_threshold=0.85),
        )

        favorite, created = service.create_from_classification(
            watch_item=watch_item(),
            topic=topic(),
            result=positive_result(confidence=0.85),
            canonical_url=canonical_url(),
        )

        assert favorite is not None
        assert created is True
        assert (
            session.query(EventORM).filter_by(event_type=EventType.NEW_FAVORITE.value).count()
            == 1
        )


def test_favorites_service_does_not_import_armas_adapter() -> None:
    service_source = Path("src/favorites/service.py").read_text(encoding="utf-8")

    assert "sources.armas_es" not in service_source
    assert "viewtopic.php" not in service_source


def test_check_unchanged_favorite_does_not_call_classifier(tmp_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)
    fetcher = FakeTopicFetcher()
    classifier = FakeClassifier()

    with session_scope(factory) as session:
        service = FavoriteService(session, topic_fetcher=fetcher, classifier=classifier)
        favorite, _ = service.create_from_classification(
            watch_item=watch_item(),
            topic=topic(),
            result=positive_result(),
            canonical_url=canonical_url(),
        )

        changed = service.check_favorite(favorite.id, watch_item=watch_item())

        assert changed is False
        assert fetcher.calls == [f"123|{canonical_url()}"]
        assert classifier.favorite_update_calls == ()
        assert session.query(EventORM).count() == 1


def test_transient_topic_fetch_error_does_not_change_availability_or_emit_events(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)
    fetcher = FakeTopicFetcher()
    fetcher.error = TopicFetchTransientError("temporary failure")

    with session_scope(factory) as session:
        service = FavoriteService(
            session,
            topic_fetcher=fetcher,
            classifier=FakeClassifier(),
        )
        favorite, _ = service.create_from_classification(
            watch_item=watch_item(),
            topic=topic(),
            result=positive_result(price=123),
            canonical_url=canonical_url(),
        )

        changed = service.check_favorite(favorite.id, watch_item=watch_item())

        assert changed is False
        assert favorite.last_checked_at is not None
        assert favorite.unavailable_confirmation_count == 0
        assert favorite.is_active is True
        assert favorite.status == AvailabilityStatus.AVAILABLE.value
        assert session.query(EventORM).count() == 1


def test_check_changed_favorite_calls_classifier_and_records_price_change(tmp_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)
    changed_topic = topic(text="Acme Target Pro rebajada a 100 EUR", post_id="789")
    fetcher = FakeTopicFetcher(changed_topic)
    classifier = FakeClassifier(
        favorite_update_results={("item_001", "123"): positive_result(price=100)}
    )

    with session_scope(factory) as session:
        service = FavoriteService(
            session,
            topic_fetcher=fetcher,
            classifier=classifier,
        )
        favorite, _ = service.create_from_classification(
            watch_item=watch_item(),
            topic=topic(),
            result=positive_result(price=123),
            canonical_url=canonical_url(),
        )

        changed = service.check_favorite(favorite.id, watch_item=watch_item())

        assert changed is True
        assert classifier.favorite_update_calls
        assert str(favorite.current_price) == "100.00"
        assert session.query(PriceHistoryORM).count() == 2
        assert (
            session.query(EventORM).filter_by(event_type=EventType.PRICE_CHANGED.value).count()
            == 1
        )


def test_title_only_change_calls_classifier(tmp_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)
    changed_topic = topic(title="Reservado Acme Target Pro")
    fetcher = FakeTopicFetcher(changed_topic)
    classifier = FakeClassifier(
        favorite_update_results={
            ("item_001", "123"): positive_result(
                price=None,
                availability=AvailabilityStatus.RESERVED,
            )
        }
    )

    with session_scope(factory) as session:
        service = FavoriteService(
            session,
            topic_fetcher=fetcher,
            classifier=classifier,
        )
        favorite, _ = service.create_from_classification(
            watch_item=watch_item(),
            topic=topic(),
            result=positive_result(price=123),
            canonical_url=canonical_url(),
        )

        changed = service.check_favorite(favorite.id, watch_item=watch_item())

        assert changed is True
        assert classifier.favorite_update_calls
        assert favorite.status == AvailabilityStatus.RESERVED.value


def test_repeated_historical_hash_can_emit_new_transition_event(tmp_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)
    changed_topic = topic(text="Acme Target Pro por 100 EUR", post_id="789")
    fetcher = FakeTopicFetcher(changed_topic)
    classifier = FakeClassifier(
        favorite_update_results={("item_001", "123"): positive_result(price=100)}
    )

    with session_scope(factory) as session:
        service = FavoriteService(
            session,
            topic_fetcher=fetcher,
            classifier=classifier,
        )
        favorite, _ = service.create_from_classification(
            watch_item=watch_item(),
            topic=topic(text="Acme Target Pro por 150 EUR"),
            result=positive_result(price=150),
            canonical_url=canonical_url(),
        )
        favorite.current_price = 200

        service.check_favorite(favorite.id, watch_item=watch_item())

        assert (
            session.query(EventORM).filter_by(event_type=EventType.PRICE_CHANGED.value).count()
            == 1
        )


def test_price_none_does_not_clear_previous_price(tmp_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)
    changed_topic = topic(text="Acme Target Pro reservado", post_id="789")
    fetcher = FakeTopicFetcher(changed_topic)
    classifier = FakeClassifier(
        favorite_update_results={
            ("item_001", "123"): positive_result(
                price=None,
                availability=AvailabilityStatus.RESERVED,
            )
        }
    )

    with session_scope(factory) as session:
        service = FavoriteService(
            session,
            topic_fetcher=fetcher,
            classifier=classifier,
        )
        favorite, _ = service.create_from_classification(
            watch_item=watch_item(),
            topic=topic(),
            result=positive_result(price=123),
            canonical_url=canonical_url(),
        )

        service.check_favorite(favorite.id, watch_item=watch_item())

        assert str(favorite.current_price) == "123.00"
        assert favorite.status == AvailabilityStatus.RESERVED.value
        assert session.query(StatusHistoryORM).count() == 2


def test_sold_or_withdrawn_deactivates_favorite(tmp_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)
    changed_topic = topic(text="Vendido", post_id="789")
    fetcher = FakeTopicFetcher(changed_topic)
    classifier = FakeClassifier(
        favorite_update_results={
            ("item_001", "123"): positive_result(
                price=None,
                availability=AvailabilityStatus.SOLD,
            )
        }
    )

    with session_scope(factory) as session:
        service = FavoriteService(
            session,
            topic_fetcher=fetcher,
            classifier=classifier,
        )
        favorite, _ = service.create_from_classification(
            watch_item=watch_item(),
            topic=topic(),
            result=positive_result(price=123),
            canonical_url=canonical_url(),
        )

        service.check_favorite(favorite.id, watch_item=watch_item())

        assert favorite.is_active is False
        assert favorite.status == AvailabilityStatus.SOLD.value
        assert (
            session.query(EventORM)
            .filter_by(event_type=EventType.BECAME_UNAVAILABLE.value)
            .count()
            == 1
        )


def test_favorite_events_do_not_store_post_text_html_or_secret_markers(tmp_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)
    sensitive_text = (
        "Acme Target Pro rebajada a 100 EUR <div>Cookie: abc "
        "Authorization: token OPENAI_API_KEY password</div>"
    )
    changed_topic = topic(text=sensitive_text, post_id="789")
    fetcher = FakeTopicFetcher(changed_topic)
    classifier = FakeClassifier(
        favorite_update_results={("item_001", "123"): positive_result(price=100)}
    )

    with session_scope(factory) as session:
        service = FavoriteService(session, topic_fetcher=fetcher, classifier=classifier)
        favorite, _ = service.create_from_classification(
            watch_item=watch_item(),
            topic=topic(text=sensitive_text),
            result=positive_result(price=123),
            canonical_url=canonical_url(),
        )

        service.check_favorite(favorite.id, watch_item=watch_item())

        payload_text = " ".join(str(event.payload_json) for event in session.query(EventORM))
        assert "Acme Target Pro rebajada" not in payload_text
        for forbidden in (
            "<div",
            "Cookie",
            "Authorization",
            "OPENAI_API_KEY",
            "password",
        ):
            assert forbidden not in payload_text


def test_withdrawn_deactivates_favorite(tmp_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)
    changed_topic = topic(text="Retirado", post_id="789")
    fetcher = FakeTopicFetcher(changed_topic)
    classifier = FakeClassifier(
        favorite_update_results={
            ("item_001", "123"): positive_result(
                price=None,
                availability=AvailabilityStatus.WITHDRAWN,
            )
        }
    )

    with session_scope(factory) as session:
        service = FavoriteService(
            session,
            topic_fetcher=fetcher,
            classifier=classifier,
        )
        favorite, _ = service.create_from_classification(
            watch_item=watch_item(),
            topic=topic(),
            result=positive_result(price=123),
            canonical_url=canonical_url(),
        )

        service.check_favorite(favorite.id, watch_item=watch_item())

        assert favorite.is_active is False
        assert favorite.status == AvailabilityStatus.WITHDRAWN.value
        assert (
            session.query(EventORM)
            .filter_by(event_type=EventType.BECAME_UNAVAILABLE.value)
            .count()
            == 1
        )


def test_unavailable_topic_requires_configured_confirmations_before_deactivation(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)
    fetcher = FakeTopicFetcher()
    fetcher.error = TopicFetchNotFoundError("not found")

    with session_scope(factory) as session:
        service = FavoriteService(
            session,
            topic_fetcher=fetcher,
            classifier=FakeClassifier(),
            config=FavoritesConfig(unavailable_confirmation_runs=2),
        )
        favorite, _ = service.create_from_classification(
            watch_item=watch_item(),
            topic=topic(),
            result=positive_result(price=123),
            canonical_url=canonical_url(),
        )

        first = service.check_favorite(favorite.id, watch_item=watch_item())
        second = service.check_favorite(favorite.id, watch_item=watch_item())

        assert first is False
        assert second is True
        assert favorite.is_active is False
        assert favorite.status == AvailabilityStatus.WITHDRAWN.value
        assert (
            session.query(EventORM).filter_by(event_type=EventType.STATUS_CHANGED.value).count()
            == 1
        )
        assert (
            session.query(EventORM)
            .filter_by(event_type=EventType.BECAME_UNAVAILABLE.value)
            .count()
            == 1
        )
