from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.models import CandidateStatus, EventType, TopicListing
from storage import create_sqlite_engine, run_migrations, session_factory, session_scope
from storage.orm import CandidateMatchORM, EventORM, TopicORM
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

        candidate = candidates.create_pending(
            topic_id=topic.id,
            watch_item_id="item_001",
            confidence=0.8,
        )
        event, created = events.create_once(
            event_type=EventType.NEW_FAVORITE,
            deduplication_key="new-favorite:123:item_001",
            topic_id=topic.id,
            watch_item_id="item_001",
        )
        app_state.set("bootstrap_completed_at", "2026-09-07T00:00:00+00:00")
        session.flush()

        assert topics.get_by_external_id("123") == topic
        assert candidate.status == CandidateStatus.PENDING.value
        assert event.id is not None
        assert created is True
        assert app_state.get("bootstrap_completed_at") == "2026-09-07T00:00:00+00:00"
