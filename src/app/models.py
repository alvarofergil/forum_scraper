"""Shared domain models and enums for Forum Scraper."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class AvailabilityStatus(StrEnum):
    """Availability states detected for a monitored listing."""

    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    SOLD = "SOLD"
    WITHDRAWN = "WITHDRAWN"
    UNKNOWN = "UNKNOWN"


class CandidateStatus(StrEnum):
    """Classification state for a candidate match."""

    PENDING = "PENDING"
    CLASSIFIED = "CLASSIFIED"
    DISCARDED = "DISCARDED"


class EventType(StrEnum):
    """Event types emitted by the v1 monitor."""

    NEW_FAVORITE = "NEW_FAVORITE"
    PRICE_CHANGED = "PRICE_CHANGED"
    STATUS_CHANGED = "STATUS_CHANGED"
    BECAME_UNAVAILABLE = "BECAME_UNAVAILABLE"
    FAVORITE_REACTIVATED = "FAVORITE_REACTIVATED"
    ERROR = "ERROR"


class ListingType(StrEnum):
    """Conceptual listing categories returned by classification."""

    OFFER = "OFFER"
    WANTED = "WANTED"
    INFORMATION = "INFORMATION"
    DISCUSSION = "DISCUSSION"
    OTHER = "OTHER"


class NotificationStatus(StrEnum):
    """Delivery state for event notifications."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class WatchItem:
    """User-configured item to watch for in forum listings."""

    id: str
    brand: str
    model: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TopicListing:
    """Structured data extracted from a forum listing row."""

    external_topic_id: str
    canonical_url: str
    title: str
    snippet: str | None = None
    author: str | None = None
    created_at: datetime | None = None
    last_activity_at: datetime | None = None
    last_post_author: str | None = None
    reply_count: int | None = None
    view_count: int | None = None


@dataclass(frozen=True, slots=True)
class TopicPost:
    """Structured data extracted from a visible post."""

    sequence_number: int
    author: str
    posted_at: datetime
    text: str
    external_post_id: str | None = None


@dataclass(frozen=True, slots=True)
class ParsedTopic:
    """Structured data extracted from a forum topic page."""

    topic_title: str
    external_topic_id: str
    original_author: str
    total_posts: int | None
    current_page: int
    total_pages: int
    posts: tuple[TopicPost, ...]


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)
