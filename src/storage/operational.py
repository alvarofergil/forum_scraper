"""Operational SQLite queries and reversible favorite actions."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EventType, NotificationStatus, utc_now
from events.service import EventService
from storage.orm import AppStateORM, CandidateMatchORM, EventORM, FavoriteORM, TopicORM


@dataclass(frozen=True, slots=True)
class OperationalStatus:
    """Small summary of monitor state for CLI status."""

    topics: int
    favorites: int
    active_favorites: int
    inactive_favorites: int
    pending_candidates: int
    events_pending: int
    events_failed: int
    events_sent: int
    state: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class FavoriteSummary:
    """Favorite row prepared for safe CLI display."""

    id: int
    topic_external_id: str
    title: str
    watch_item_id: str
    status: str
    is_active: bool
    current_price: str
    currency: str
    canonical_url: str


@dataclass(frozen=True, slots=True)
class TopicInspection:
    """Safe topic detail for CLI inspection."""

    topic: TopicORM
    favorite: FavoriteORM | None
    events: tuple[EventORM, ...]


@dataclass(frozen=True, slots=True)
class FavoriteActionResult:
    """Result of a reversible favorite activation change."""

    favorite: FavoriteORM
    changed: bool


def read_status(session: Session) -> OperationalStatus:
    """Return aggregate monitor state without exposing sensitive payloads."""

    return OperationalStatus(
        topics=_count(session, TopicORM),
        favorites=_count(session, FavoriteORM),
        active_favorites=_count(session, FavoriteORM, FavoriteORM.is_active.is_(True)),
        inactive_favorites=_count(session, FavoriteORM, FavoriteORM.is_active.is_(False)),
        pending_candidates=_count(
            session,
            CandidateMatchORM,
            CandidateMatchORM.status == "PENDING",
        ),
        events_pending=_event_count(session, NotificationStatus.PENDING),
        events_failed=_event_count(session, NotificationStatus.FAILED),
        events_sent=_event_count(session, NotificationStatus.SENT),
        state=tuple(
            session.execute(select(AppStateORM.key, AppStateORM.value).order_by(AppStateORM.key))
        ),
    )


def list_favorites(session: Session) -> list[FavoriteSummary]:
    """List favorites with their topic metadata."""

    rows = session.execute(
        select(FavoriteORM, TopicORM)
        .join(TopicORM, FavoriteORM.topic_id == TopicORM.id)
        .order_by(FavoriteORM.is_active.desc(), FavoriteORM.id)
    )
    return [_favorite_summary(favorite, topic) for favorite, topic in rows]


def inspect_topic(session: Session, topic_identifier: str) -> TopicInspection | None:
    """Inspect one topic by external id first, then numeric database id."""

    topic = _topic_by_identifier(session, topic_identifier)
    if topic is None:
        return None

    favorite = session.scalar(select(FavoriteORM).where(FavoriteORM.topic_id == topic.id))
    events = tuple(
        session.scalars(
            select(EventORM)
            .where(EventORM.topic_id == topic.id)
            .order_by(EventORM.created_at, EventORM.id)
        )
    )
    return TopicInspection(topic=topic, favorite=favorite, events=events)


def deactivate_favorite(session: Session, topic_identifier: str) -> FavoriteActionResult | None:
    """Deactivate a favorite reversibly and emit one audit event for the transition."""

    favorite = _favorite_by_topic_identifier(session, topic_identifier)
    if favorite is None:
        return None
    if not favorite.is_active:
        return FavoriteActionResult(favorite=favorite, changed=False)

    favorite.is_active = False
    favorite.updated_at = utc_now()
    _emit_manual_favorite_event(
        session,
        favorite,
        event_type=EventType.BECAME_UNAVAILABLE,
        action="manual_deactivate",
    )
    session.flush()
    return FavoriteActionResult(favorite=favorite, changed=True)


def reactivate_favorite(session: Session, topic_identifier: str) -> FavoriteActionResult | None:
    """Reactivate a favorite reversibly and emit one audit event for the transition."""

    favorite = _favorite_by_topic_identifier(session, topic_identifier)
    if favorite is None:
        return None
    if favorite.is_active:
        return FavoriteActionResult(favorite=favorite, changed=False)

    favorite.is_active = True
    favorite.updated_at = utc_now()
    _emit_manual_favorite_event(
        session,
        favorite,
        event_type=EventType.FAVORITE_REACTIVATED,
        action="manual_reactivate",
    )
    session.flush()
    return FavoriteActionResult(favorite=favorite, changed=True)


def backup_sqlite_database(source_path: str | Path, destination_path: str | Path) -> Path:
    """Create a consistent SQLite backup using the native backup API."""

    source = Path(source_path)
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as source_connection:
        with sqlite3.connect(destination) as destination_connection:
            source_connection.backup(destination_connection)
    return destination


def _count(session: Session, model: type[object], *criteria: object) -> int:
    stmt = select(func.count()).select_from(model)
    for criterion in criteria:
        stmt = stmt.where(criterion)
    return int(session.scalar(stmt) or 0)


def _event_count(session: Session, status: NotificationStatus) -> int:
    return _count(session, EventORM, EventORM.notification_status == status.value)


def _topic_by_identifier(session: Session, topic_identifier: str) -> TopicORM | None:
    topic = session.scalar(
        select(TopicORM).where(TopicORM.external_topic_id == topic_identifier)
    )
    if topic is not None:
        return topic
    try:
        topic_id = int(topic_identifier)
    except ValueError:
        return None
    return session.get(TopicORM, topic_id)


def _favorite_by_topic_identifier(
    session: Session,
    topic_identifier: str,
) -> FavoriteORM | None:
    topic = _topic_by_identifier(session, topic_identifier)
    if topic is None:
        return None
    return session.scalar(select(FavoriteORM).where(FavoriteORM.topic_id == topic.id))


def _favorite_summary(favorite: FavoriteORM, topic: TopicORM) -> FavoriteSummary:
    return FavoriteSummary(
        id=favorite.id,
        topic_external_id=topic.external_topic_id,
        title=topic.title,
        watch_item_id=favorite.watch_item_id,
        status=favorite.status,
        is_active=favorite.is_active,
        current_price=str(favorite.current_price) if favorite.current_price is not None else "-",
        currency=favorite.currency or "-",
        canonical_url=topic.canonical_url,
    )


def _emit_manual_favorite_event(
    session: Session,
    favorite: FavoriteORM,
    *,
    event_type: EventType,
    action: str,
) -> None:
    timestamp = utc_now().isoformat().replace("+00:00", "Z")
    topic = favorite.topic
    EventService(session).emit(
        event_type=event_type,
        deduplication_key=f"favorite:{favorite.id}|action:{action}|at:{timestamp}",
        topic_id=favorite.topic_id,
        favorite_id=favorite.id,
        watch_item_id=favorite.watch_item_id,
        payload={
            "action": action,
            "topic_external_id": topic.external_topic_id if topic is not None else None,
            "favorite_id": favorite.id,
            "is_active": favorite.is_active,
        },
    )
