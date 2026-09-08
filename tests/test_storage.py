from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, StatementError

from alembic import command
from app.models import CandidateStatus, EventType, TopicListing
from storage import create_sqlite_engine, run_migrations, session_factory, session_scope
from storage.orm import CandidateMatchORM, EventORM, FavoriteORM, TopicORM
from storage.repositories import (
    AppStateRepository,
    CandidateMatchRepository,
    EventRepository,
    TopicRepository,
)

EXPECTED_TABLES = {
    "topics",
    "candidate_matches",
    "favorites",
    "price_history",
    "status_history",
    "topic_posts",
    "events",
    "app_state",
}


@pytest.fixture()
def migrated_db_path(tmp_path: Path) -> Path:
    db_path = tmp_path / "monitor.db"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(config, "head")
    return db_path


def test_initial_migration_creates_all_tables(migrated_db_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path)

    assert EXPECTED_TABLES.issubset(set(inspect(engine).get_table_names()))


def test_run_migrations_helper_creates_database(tmp_path: Path) -> None:
    db_path = tmp_path / "from-helper.db"

    run_migrations(db_path)
    engine = create_sqlite_engine(db_path)

    assert EXPECTED_TABLES.issubset(set(inspect(engine).get_table_names()))


def test_run_migrations_helper_leaves_database_ready_for_app_pragmas(tmp_path: Path) -> None:
    db_path = tmp_path / "from-helper.db"

    run_migrations(db_path)
    engine = create_sqlite_engine(db_path)

    with engine.connect() as connection:
        foreign_keys = connection.execute(text("PRAGMA foreign_keys")).scalar_one()
        journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar_one()

    assert foreign_keys == 1
    assert journal_mode == "wal"


def test_corrective_migration_adds_favorite_and_event_columns(migrated_db_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path)
    inspector = inspect(engine)

    favorite_columns = {column["name"] for column in inspector.get_columns("favorites")}
    event_columns = {column["name"] for column in inspector.get_columns("events")}

    assert {"is_active", "last_checked_at", "last_content_hash", "last_classified_at"}.issubset(
        favorite_columns
    )
    assert "payload_json" in event_columns


def test_sqlite_pragmas_enable_foreign_keys_and_wal(migrated_db_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path)

    with engine.connect() as connection:
        foreign_keys = connection.execute(text("PRAGMA foreign_keys")).scalar_one()
        journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar_one()

    assert foreign_keys == 1
    assert journal_mode == "wal"


def test_external_topic_id_is_unique(migrated_db_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path)
    factory = session_factory(engine)

    with session_scope(factory) as session:
        session.add_all(
            [
                TopicORM(
                    external_topic_id="123",
                    canonical_url="https://www.armas.es/foros/viewtopic.php?f=96&t=123",
                    title="Topic",
                ),
                TopicORM(
                    external_topic_id="123",
                    canonical_url="https://www.armas.es/foros/viewtopic.php?f=96&t=123",
                    title="Duplicate",
                ),
            ]
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_candidate_is_unique_per_topic_and_watch_item(migrated_db_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path)
    factory = session_factory(engine)

    with session_scope(factory) as session:
        topic = TopicORM(
            external_topic_id="123",
            canonical_url="https://www.armas.es/foros/viewtopic.php?f=96&t=123",
            title="Topic",
        )
        session.add(topic)
        session.flush()
        session.add_all(
            [
                CandidateMatchORM(topic_id=topic.id, watch_item_id="item_001"),
                CandidateMatchORM(topic_id=topic.id, watch_item_id="item_001"),
            ]
        )

        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_event_deduplication_key_is_unique(migrated_db_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path)
    factory = session_factory(engine)

    with session_scope(factory) as session:
        session.add_all(
            [
                EventORM(
                    event_type=EventType.ERROR.value,
                    deduplication_key="same-key",
                ),
                EventORM(
                    event_type=EventType.ERROR.value,
                    deduplication_key="same-key",
                ),
            ]
        )

        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_foreign_keys_are_enforced(migrated_db_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path)
    factory = session_factory(engine)

    with session_scope(factory) as session:
        session.add(CandidateMatchORM(topic_id=999, watch_item_id="item_001"))

        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_sqlite_datetime_round_trip_preserves_aware_utc(migrated_db_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path)
    factory = session_factory(engine)
    timestamp = datetime(2026, 9, 7, 12, 30, tzinfo=UTC)

    with session_scope(factory) as session:
        topic = TopicORM(
            external_topic_id="utc-topic",
            canonical_url="https://www.armas.es/foros/viewtopic.php?f=96&t=utc-topic",
            title="UTC Topic",
            created_at=timestamp,
            last_activity_at=timestamp,
        )
        session.add(topic)
        session.flush()
        topic_id = topic.id

    with session_scope(factory) as session:
        stored = session.get(TopicORM, topic_id)

        assert stored is not None
        assert stored.created_at == timestamp
        assert stored.created_at.tzinfo is UTC
        assert stored.first_seen_at.tzinfo is UTC


def test_sqlite_datetime_rejects_naive_values(migrated_db_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path)
    factory = session_factory(engine)

    with session_scope(factory) as session:
        session.add(
            TopicORM(
                external_topic_id="naive-topic",
                canonical_url="https://www.armas.es/foros/viewtopic.php?f=96&t=naive-topic",
                title="Naive Topic",
                created_at=datetime(2026, 9, 7, 12, 30),
            )
        )

        with pytest.raises(StatementError, match="timezone-aware"):
            session.flush()
        session.rollback()


def test_favorite_operational_fields_round_trip(migrated_db_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path)
    factory = session_factory(engine)
    checked_at = datetime(2026, 9, 7, 12, 30, tzinfo=UTC)

    with session_scope(factory) as session:
        topic = TopicORM(
            external_topic_id="fav-topic",
            canonical_url="https://www.armas.es/foros/viewtopic.php?f=96&t=fav-topic",
            title="Favorite Topic",
        )
        session.add(topic)
        session.flush()
        favorite = FavoriteORM(
            topic_id=topic.id,
            watch_item_id="item_001",
            is_active=False,
            last_checked_at=checked_at,
            last_content_hash="abc123",
            last_classified_at=checked_at,
        )
        session.add(favorite)
        session.flush()
        favorite_id = favorite.id

    with session_scope(factory) as session:
        stored = session.get(FavoriteORM, favorite_id)

        assert stored is not None
        assert stored.is_active is False
        assert stored.last_checked_at == checked_at
        assert stored.last_checked_at.tzinfo is UTC
        assert stored.last_content_hash == "abc123"


def test_repositories_provide_minimal_operations(migrated_db_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path)
    factory = session_factory(engine)

    with session_scope(factory) as session:
        topics = TopicRepository(session)
        candidates = CandidateMatchRepository(session)
        events = EventRepository(session)
        app_state = AppStateRepository(session)

        topic = topics.upsert_listing(
            TopicListing(
                external_topic_id="123",
                canonical_url="https://www.armas.es/foros/viewtopic.php?f=96&t=123",
                title="Topic",
            )
        )
        session.flush()

        candidate, candidate_created = candidates.get_or_create_pending(
            topic_id=topic.id,
            watch_item_id="item_001",
            confidence=0.8,
        )
        event, created = events.create_once(
            event_type=EventType.NEW_FAVORITE,
            deduplication_key="new-favorite:123:item_001",
            topic_id=topic.id,
            watch_item_id="item_001",
            payload={"watch_item_id": "item_001", "topic": {"id": "123"}},
        )
        app_state.set("bootstrap_completed_at", "2026-09-07T00:00:00+00:00")
        session.flush()

        assert topics.get_by_external_id("123") == topic
        assert candidate.status == CandidateStatus.PENDING.value
        assert candidate_created is True
        assert event.id is not None
        assert event.payload_json == {"topic": {"id": "123"}, "watch_item_id": "item_001"}
        raw_payload = session.execute(
            text("SELECT payload_json FROM events WHERE id = :event_id"),
            {"event_id": event.id},
        ).scalar_one()
        assert raw_payload == '{"topic":{"id":"123"},"watch_item_id":"item_001"}'
        assert created is True
        assert app_state.get("bootstrap_completed_at") == "2026-09-07T00:00:00+00:00"


def test_candidate_get_or_create_pending_is_idempotent(migrated_db_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path)
    factory = session_factory(engine)

    with session_scope(factory) as session:
        topic = TopicORM(
            external_topic_id="candidate-topic",
            canonical_url="https://www.armas.es/foros/viewtopic.php?f=96&t=candidate-topic",
            title="Candidate Topic",
        )
        session.add(topic)
        session.flush()

        repo = CandidateMatchRepository(session)
        first, first_created = repo.get_or_create_pending(
            topic_id=topic.id,
            watch_item_id="item_001",
            confidence=0.8,
        )
        second, second_created = repo.get_or_create_pending(
            topic_id=topic.id,
            watch_item_id="item_001",
            confidence=0.1,
        )

        assert first.id == second.id
        assert first_created is True
        assert second_created is False
        assert second.confidence == 0.8


def test_topic_upsert_listing_preserves_metadata_when_partial_listing_has_none(
    migrated_db_path: Path,
) -> None:
    engine = create_sqlite_engine(migrated_db_path)
    factory = session_factory(engine)
    created_at = datetime(2026, 9, 7, 12, 30, tzinfo=UTC)

    with session_scope(factory) as session:
        repo = TopicRepository(session)
        topic = repo.upsert_listing(
            TopicListing(
                external_topic_id="partial-topic",
                canonical_url="https://www.armas.es/foros/viewtopic.php?f=96&t=partial-topic",
                title="Initial title",
                snippet="initial snippet",
                author="initial author",
                created_at=created_at,
                last_activity_at=created_at,
                last_post_author="last author",
                reply_count=3,
                view_count=40,
            )
        )
        session.flush()

        repo.upsert_listing(
            TopicListing(
                external_topic_id="partial-topic",
                canonical_url="https://www.armas.es/foros/viewtopic.php?f=96&t=partial-topic",
                title="Updated title",
            )
        )
        session.flush()

        assert topic.title == "Updated title"
        assert topic.snippet == "initial snippet"
        assert topic.author == "initial author"
        assert topic.created_at == created_at
        assert topic.last_activity_at == created_at
        assert topic.last_post_author == "last author"
        assert topic.reply_count == 3
        assert topic.view_count == 40
