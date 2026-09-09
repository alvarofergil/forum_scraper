from __future__ import annotations

from pathlib import Path

from alembic.config import Config

from alembic import command
from app.models import EventType, NotificationStatus
from events.service import (
    EventService,
    build_deduplication_key,
    sanitize_error_message,
    stable_payload,
)
from storage import create_sqlite_engine, session_factory, session_scope
from storage.orm import EventORM, TopicORM


def migrated_db_path(tmp_path: Path) -> Path:
    db_path = tmp_path / "monitor.db"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(config, "head")
    return db_path


def create_topic(session) -> TopicORM:  # type: ignore[no-untyped-def]
    topic = TopicORM(
        external_topic_id="123",
        canonical_url="https://www.armas.es/foros/viewtopic.php?f=96&t=123",
        title="Topic",
    )
    session.add(topic)
    session.flush()
    return topic


def test_stable_payload_sorts_nested_keys_without_mutating_input() -> None:
    payload = {"z": 1, "a": {"b": 2, "a": 1}, "items": [{"y": 2, "x": 1}]}

    normalized = stable_payload(payload)

    assert list(normalized) == ["a", "items", "z"]
    assert list(normalized["a"]) == ["a", "b"]
    assert list(normalized["items"][0]) == ["x", "y"]
    assert list(payload) == ["z", "a", "items"]


def test_build_deduplication_key_is_stable() -> None:
    key = build_deduplication_key(
        topic_external_id="123",
        event_type=EventType.PRICE_CHANGED,
        content_hash="abc",
        watch_item_id="item_001",
    )

    assert key == "topic:123|watch:item_001|event:PRICE_CHANGED|hash:abc"


def test_emit_same_event_twice_does_not_duplicate(tmp_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)

    with session_scope(factory) as session:
        topic = create_topic(session)
        service = EventService(session)

        first, first_created = service.emit(
            event_type=EventType.NEW_FAVORITE,
            deduplication_key="topic:123|event:NEW_FAVORITE|hash:abc",
            topic_id=topic.id,
            watch_item_id="item_001",
            payload={"b": 2, "a": 1},
        )
        second, second_created = service.emit(
            event_type=EventType.NEW_FAVORITE,
            deduplication_key="topic:123|event:NEW_FAVORITE|hash:abc",
            topic_id=topic.id,
            watch_item_id="item_001",
            payload={"a": 1, "b": 2},
        )

        assert first.id == second.id
        assert first_created is True
        assert second_created is False
        assert session.query(EventORM).count() == 1
        assert first.notification_status == NotificationStatus.PENDING.value


def test_different_events_for_same_topic_can_coexist(tmp_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)

    with session_scope(factory) as session:
        topic = create_topic(session)
        service = EventService(session)

        price, price_created = service.emit_for_topic(
            event_type=EventType.PRICE_CHANGED,
            topic_external_id=topic.external_topic_id,
            content_hash="same-hash",
            topic_id=topic.id,
            payload={"new_price": 100},
        )
        status, status_created = service.emit_for_topic(
            event_type=EventType.STATUS_CHANGED,
            topic_external_id=topic.external_topic_id,
            content_hash="same-hash",
            topic_id=topic.id,
            payload={"new_status": "RESERVED"},
        )

        assert price.id != status.id
        assert price_created is True
        assert status_created is True
        assert session.query(EventORM).count() == 2


def test_payload_is_stored_deterministically(tmp_path: Path) -> None:
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)

    with session_scope(factory) as session:
        topic = create_topic(session)
        service = EventService(session)

        event, created = service.emit_for_topic(
            event_type=EventType.ERROR,
            topic_external_id=topic.external_topic_id,
            content_hash="err-hash",
            topic_id=topic.id,
            payload={"z": 1, "a": {"b": 2, "a": 1}},
            error_message="temporary failure",
        )
        session.flush()

        assert created is True
        assert event.payload_json == {"a": {"a": 1, "b": 2}, "z": 1}
        assert event.error_message == "temporary failure"


def test_sanitize_error_message_redacts_secrets_and_html() -> None:
    cases = (
        OSError("SMTP password=abc"),
        RuntimeError("Authorization: Bearer secret-token"),
        RuntimeError("OPENAI_API_KEY=sk-secret"),
        RuntimeError("HTTP 500 <html><body>private vendor page</body></html>"),
        RuntimeError("Cookie: session=abc token=hidden api_key: abc secret=value"),
    )

    for case in cases:
        sanitized = sanitize_error_message(case)
        lowered = sanitized.lower()
        assert "abc" not in sanitized
        assert "secret-token" not in sanitized
        assert "sk-secret" not in sanitized
        assert "<html" not in lowered
        assert "<body" not in lowered
        assert "private vendor page" not in sanitized
        for marker in ("OPENAI_API_KEY", "Authorization", "Cookie", "password", "token"):
            assert marker.lower() not in lowered
