"""SQLAlchemy ORM models for Forum Scraper persistence."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.models import AvailabilityStatus, CandidateStatus, NotificationStatus, utc_now
from storage.types import JsonPayload, JSONPayloadType, UTCDateTime


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class TopicORM(Base):
    """Forum topic metadata without full post text."""

    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_topic_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    canonical_url: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    snippet: Mapped[str | None] = mapped_column(String(1000))
    author: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_activity_at: Mapped[datetime | None] = mapped_column(UTCDateTime, index=True)
    last_post_author: Mapped[str | None] = mapped_column(String(255))
    reply_count: Mapped[int | None] = mapped_column(Integer)
    view_count: Mapped[int | None] = mapped_column(Integer)
    first_seen_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utc_now,
        onupdate=utc_now,
    )

    candidate_matches: Mapped[list[CandidateMatchORM]] = relationship(
        back_populates="topic",
        cascade="all, delete-orphan",
    )
    favorite: Mapped[FavoriteORM | None] = relationship(back_populates="topic")
    posts: Mapped[list[TopicPostORM]] = relationship(
        back_populates="topic",
        cascade="all, delete-orphan",
    )
    events: Mapped[list[EventORM]] = relationship(back_populates="topic")


class CandidateMatchORM(Base):
    """Potential match between a topic and a configured watch item."""

    __tablename__ = "candidate_matches"
    __table_args__ = (
        UniqueConstraint("topic_id", "watch_item_id", name="uq_candidate_topic_watch_item"),
        CheckConstraint(
            "status IN ('PENDING', 'CLASSIFIED', 'DISCARDED')",
            name="ck_candidate_matches_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
    )
    watch_item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=CandidateStatus.PENDING.value,
    )
    confidence: Mapped[float | None] = mapped_column(Float)
    matched_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
    classified_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    topic: Mapped[TopicORM] = relationship(back_populates="candidate_matches")


class FavoriteORM(Base):
    """Topic selected for ongoing monitoring."""

    __tablename__ = "favorites"
    __table_args__ = (
        CheckConstraint(
            "status IN ('AVAILABLE', 'RESERVED', 'SOLD', 'WITHDRAWN', 'UNKNOWN')",
            name="ck_favorites_status",
        ),
        CheckConstraint(
            "unavailable_confirmation_count >= 0",
            name="ck_favorites_unavailable_confirmation_count",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    watch_item_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AvailabilityStatus.UNKNOWN.value,
    )
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    price_updated_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_content_hash: Mapped[str | None] = mapped_column(String(128))
    last_classified_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    unavailable_confirmation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utc_now,
        onupdate=utc_now,
    )

    topic: Mapped[TopicORM] = relationship(back_populates="favorite")
    price_history: Mapped[list[PriceHistoryORM]] = relationship(
        back_populates="favorite",
        cascade="all, delete-orphan",
    )
    status_history: Mapped[list[StatusHistoryORM]] = relationship(
        back_populates="favorite",
        cascade="all, delete-orphan",
    )
    events: Mapped[list[EventORM]] = relationship(back_populates="favorite")


class PriceHistoryORM(Base):
    """Historical price observations for a favorite."""

    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    favorite_id: Mapped[int] = mapped_column(
        ForeignKey("favorites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    detected_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
    source_hash: Mapped[str | None] = mapped_column(String(128))

    favorite: Mapped[FavoriteORM] = relationship(back_populates="price_history")


class StatusHistoryORM(Base):
    """Historical availability observations for a favorite."""

    __tablename__ = "status_history"
    __table_args__ = (
        CheckConstraint(
            "status IN ('AVAILABLE', 'RESERVED', 'SOLD', 'WITHDRAWN', 'UNKNOWN')",
            name="ck_status_history_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    favorite_id: Mapped[int] = mapped_column(
        ForeignKey("favorites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)

    favorite: Mapped[FavoriteORM] = relationship(back_populates="status_history")


class TopicPostORM(Base):
    """Persisted post metadata and content hash, without full text."""

    __tablename__ = "topic_posts"
    __table_args__ = (
        UniqueConstraint("topic_id", "sequence_number", name="uq_topic_posts_sequence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_post_id: Mapped[str | None] = mapped_column(String(64))
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    author: Mapped[str | None] = mapped_column(String(255))
    posted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    seen_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)

    topic: Mapped[TopicORM] = relationship(back_populates="posts")


class EventORM(Base):
    """Deduplicated event pending optional notification."""

    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('NEW_FAVORITE', 'PRICE_CHANGED', 'STATUS_CHANGED', "
            "'BECAME_UNAVAILABLE', 'FAVORITE_REACTIVATED', 'ERROR')",
            name="ck_events_event_type",
        ),
        CheckConstraint(
            "notification_status IN ('PENDING', 'SENT', 'FAILED')",
            name="ck_events_notification_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    deduplication_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))
    favorite_id: Mapped[int | None] = mapped_column(ForeignKey("favorites.id", ondelete="SET NULL"))
    watch_item_id: Mapped[str | None] = mapped_column(String(255))
    payload_json: Mapped[JsonPayload | None] = mapped_column(JSONPayloadType)
    notification_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=NotificationStatus.PENDING.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utc_now,
        index=True,
    )
    notified_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    error_message: Mapped[str | None] = mapped_column(String(1000))

    topic: Mapped[TopicORM | None] = relationship(back_populates="events")
    favorite: Mapped[FavoriteORM | None] = relationship(back_populates="events")


class AppStateORM(Base):
    """Small key-value state for operational cursors."""

    __tablename__ = "app_state"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(String(1000), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utc_now,
        onupdate=utc_now,
    )
