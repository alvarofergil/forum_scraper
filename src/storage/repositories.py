"""Minimal repositories for future services to share persistence access."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CandidateStatus, EventType, NotificationStatus, TopicListing, utc_now
from storage.orm import AppStateORM, CandidateMatchORM, EventORM, TopicORM
from storage.types import JsonPayload


class TopicRepository:
    """Persistence helpers for topic metadata."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_external_id(self, external_topic_id: str) -> TopicORM | None:
        stmt = select(TopicORM).where(TopicORM.external_topic_id == external_topic_id)
        return self.session.scalar(stmt)

    def upsert_listing(self, listing: TopicListing) -> TopicORM:
        topic = self.get_by_external_id(listing.external_topic_id)
        if topic is None:
            topic = TopicORM(
                external_topic_id=listing.external_topic_id,
                canonical_url=listing.canonical_url,
                title=listing.title,
            )
            self.session.add(topic)

        topic.canonical_url = listing.canonical_url
        topic.title = listing.title
        if listing.snippet is not None:
            topic.snippet = listing.snippet
        if listing.author is not None:
            topic.author = listing.author
        if listing.created_at is not None:
            topic.created_at = listing.created_at
        if listing.last_activity_at is not None:
            topic.last_activity_at = listing.last_activity_at
        if listing.last_post_author is not None:
            topic.last_post_author = listing.last_post_author
        if listing.reply_count is not None:
            topic.reply_count = listing.reply_count
        if listing.view_count is not None:
            topic.view_count = listing.view_count
        topic.updated_at = utc_now()
        return topic


class CandidateMatchRepository:
    """Persistence helpers for topic/watchlist candidate matches."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_pending(
        self,
        *,
        topic_id: int,
        watch_item_id: str,
        confidence: float | None = None,
    ) -> CandidateMatchORM:
        candidate = CandidateMatchORM(
            topic_id=topic_id,
            watch_item_id=watch_item_id,
            status=CandidateStatus.PENDING.value,
            confidence=confidence,
        )
        self.session.add(candidate)
        return candidate

    def get_or_create_pending(
        self,
        *,
        topic_id: int,
        watch_item_id: str,
        confidence: float | None = None,
    ) -> tuple[CandidateMatchORM, bool]:
        existing = self.session.scalar(
            select(CandidateMatchORM).where(
                CandidateMatchORM.topic_id == topic_id,
                CandidateMatchORM.watch_item_id == watch_item_id,
            )
        )
        if existing is not None:
            return existing, False

        candidate = self.create_pending(
            topic_id=topic_id,
            watch_item_id=watch_item_id,
            confidence=confidence,
        )
        self.session.flush()
        return candidate, True


class EventRepository:
    """Persistence helpers for deduplicated events."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_once(
        self,
        *,
        event_type: EventType,
        deduplication_key: str,
        topic_id: int | None = None,
        favorite_id: int | None = None,
        watch_item_id: str | None = None,
        payload: JsonPayload | None = None,
    ) -> tuple[EventORM, bool]:
        existing = self.session.scalar(
            select(EventORM).where(EventORM.deduplication_key == deduplication_key)
        )
        if existing is not None:
            return existing, False

        event = EventORM(
            event_type=event_type.value,
            deduplication_key=deduplication_key,
            topic_id=topic_id,
            favorite_id=favorite_id,
            watch_item_id=watch_item_id,
            payload_json=payload,
            notification_status=NotificationStatus.PENDING.value,
        )
        self.session.add(event)
        self.session.flush()
        return event, True


class AppStateRepository:
    """Persistence helpers for small operational state values."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, key: str) -> str | None:
        row = self.session.get(AppStateORM, key)
        if row is None:
            return None
        return row.value

    def set(self, key: str, value: str) -> AppStateORM:
        row = self.session.get(AppStateORM, key)
        if row is None:
            row = AppStateORM(key=key, value=value)
            self.session.add(row)
        else:
            row.value = value
            row.updated_at = utc_now()
        return row
