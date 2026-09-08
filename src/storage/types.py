"""Custom SQLAlchemy types for SQLite persistence boundaries."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Text
from sqlalchemy.types import TypeDecorator

JsonPayload = Mapping[str, Any]


class UTCDateTime(TypeDecorator[datetime]):
    """Store timezone-aware datetimes and return them normalized to UTC."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime values persisted by Forum Scraper must be timezone-aware")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class JSONPayloadType(TypeDecorator[JsonPayload]):
    """Persist event payloads as stable JSON text."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: JsonPayload | None, dialect: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, Mapping):
            raise ValueError("event payload_json must be a mapping")
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def process_result_value(self, value: str | None, dialect: object) -> JsonPayload | None:
        if value is None:
            return None
        loaded = json.loads(value)
        if not isinstance(loaded, dict):
            raise ValueError("event payload_json must decode to a mapping")
        return loaded
