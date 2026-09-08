"""Event creation service with deterministic deduplication."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy.orm import Session

from app.models import EventType
from storage.orm import EventORM
from storage.repositories import EventRepository
from storage.types import JsonPayload


def build_deduplication_key(
    *,
    topic_external_id: str,
    event_type: EventType,
    content_hash: str,
    watch_item_id: str | None = None,
) -> str:
    """Build the default stable event key used by favorite/discovery services."""

    parts = [f"topic:{topic_external_id}"]
    if watch_item_id is not None:
        parts.append(f"watch:{watch_item_id}")
    parts.extend([f"event:{event_type.value}", f"hash:{content_hash}"])
    return "|".join(parts)


def stable_payload(payload: JsonPayload | None) -> JsonPayload | None:
    """Return a recursively key-sorted payload without changing values."""

    if payload is None:
        return None
    return _normalize_payload(payload)


class EventService:
    """Create deduplicated events pending notification."""

    def __init__(self, session: Session) -> None:
        self._repository = EventRepository(session)

    def emit(
        self,
        *,
        event_type: EventType,
        deduplication_key: str,
        topic_id: int | None = None,
        favorite_id: int | None = None,
        watch_item_id: str | None = None,
        payload: JsonPayload | None = None,
        error_message: str | None = None,
    ) -> tuple[EventORM, bool]:
        """Create an event once, keyed by the provided deduplication key."""

        if not deduplication_key.strip():
            raise ValueError("deduplication_key must not be empty")
        event, created = self._repository.create_once(
            event_type=event_type,
            deduplication_key=deduplication_key,
            topic_id=topic_id,
            favorite_id=favorite_id,
            watch_item_id=watch_item_id,
            payload=stable_payload(payload),
        )
        if created and error_message is not None:
            event.error_message = error_message
        return event, created

    def emit_for_topic(
        self,
        *,
        event_type: EventType,
        topic_external_id: str,
        content_hash: str,
        topic_id: int | None = None,
        favorite_id: int | None = None,
        watch_item_id: str | None = None,
        payload: JsonPayload | None = None,
        error_message: str | None = None,
    ) -> tuple[EventORM, bool]:
        """Create an event using the default topic/event/hash deduplication key."""

        return self.emit(
            event_type=event_type,
            deduplication_key=build_deduplication_key(
                topic_external_id=topic_external_id,
                watch_item_id=watch_item_id,
                event_type=event_type,
                content_hash=content_hash,
            ),
            topic_id=topic_id,
            favorite_id=favorite_id,
            watch_item_id=watch_item_id,
            payload=payload,
            error_message=error_message,
        )


def _normalize_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _normalize_payload(value[key]) for key in sorted(value)}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_normalize_payload(item) for item in value]
    return value
