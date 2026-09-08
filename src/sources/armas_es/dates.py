"""Date parsing helpers for armas.es forum pages."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

FORUM_TIMEZONE = ZoneInfo("Europe/Madrid")

SPANISH_MONTHS = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}


class ArmasDateError(ValueError):
    """Raised when an armas.es date cannot be parsed."""


def parse_forum_datetime(value: str) -> datetime:
    """Parse an armas.es visible date and return a timezone-aware UTC datetime."""

    parts = value.strip().split()
    if len(parts) != 4:
        raise ArmasDateError(f"unsupported forum date: {value!r}")

    day_text, month_text, year_text, time_text = parts
    try:
        hour_text, minute_text = time_text.split(":", maxsplit=1)
        month = SPANISH_MONTHS[month_text.lower()]
        local_datetime = datetime(
            int(year_text),
            month,
            int(day_text),
            int(hour_text),
            int(minute_text),
            tzinfo=FORUM_TIMEZONE,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ArmasDateError(f"unsupported forum date: {value!r}") from exc

    return local_datetime.astimezone(UTC)
