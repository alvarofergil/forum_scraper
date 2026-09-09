from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic.config import Config

from alembic import command
from app import cli
from app.config import (
    AiConfig,
    AppConfig,
    BootstrapConfig,
    DebugConfig,
    DiscoveryConfig,
    FavoritesConfig,
    NotificationsConfig,
    ScrapingConfig,
    SourceConfig,
)
from app.models import AvailabilityStatus, EventType, NotificationStatus, WatchItem
from events.service import EventService
from storage import create_sqlite_engine, session_factory, session_scope
from storage.orm import FavoriteORM, TopicORM


def migrated_db_path(tmp_path: Path) -> Path:
    db_path = tmp_path / "monitor.db"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(config, "head")
    return db_path


def config() -> AppConfig:
    return AppConfig(
        source=SourceConfig(type="armas_es", base_url="https://www.armas.es", forum_id=96),
        bootstrap=BootstrapConfig(pages=1),
        discovery=DiscoveryConfig(),
        favorites=FavoritesConfig(),
        scraping=ScrapingConfig(request_delay_seconds=0),
        ai=AiConfig(enabled=False),
        notifications=NotificationsConfig(),
        debug=DebugConfig(),
        watchlist=(WatchItem(id="watch-001", brand="Acme", model="Target Pro"),),
    )


def fail_load_config(_path: str) -> AppConfig:
    raise AssertionError("config not required")


def seed_operational_db(db_path: Path) -> None:
    engine = create_sqlite_engine(db_path)
    factory = session_factory(engine)
    with session_scope(factory) as session:
        topic = TopicORM(
            external_topic_id="topic-123",
            canonical_url="https://www.armas.es/foros/viewtopic.php?f=96&t=topic-123",
            title="Vendo Acme Target Pro",
            snippet="Resumen publico del anuncio",
            author="seller",
        )
        session.add(topic)
        session.flush()
        favorite = FavoriteORM(
            topic_id=topic.id,
            watch_item_id="watch-001",
            status=AvailabilityStatus.AVAILABLE.value,
            current_price=120,
            currency="EUR",
            is_active=True,
        )
        session.add(favorite)
        session.flush()
        EventService(session).emit_for_topic(
            event_type=EventType.NEW_FAVORITE,
            topic_external_id=topic.external_topic_id,
            content_hash="abc",
            topic_id=topic.id,
            favorite_id=favorite.id,
            watch_item_id=favorite.watch_item_id,
            payload={"title": topic.title},
        )


def test_status_cli_prints_database_summary(monkeypatch, capsys, tmp_path: Path) -> None:
    db_path = migrated_db_path(tmp_path)
    seed_operational_db(db_path)
    monkeypatch.setattr(cli, "load_config", fail_load_config)
    monkeypatch.setattr(cli, "run_migrations", lambda _database: None)

    exit_code = cli.main(["--database", str(db_path), "status"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "status: topics=1 favorites=1 active_favorites=1 inactive_favorites=0" in output
    assert "events_pending=1 events_failed=0 events_sent=0" in output


def test_favorites_cli_lists_favorites(monkeypatch, capsys, tmp_path: Path) -> None:
    db_path = migrated_db_path(tmp_path)
    seed_operational_db(db_path)
    monkeypatch.setattr(cli, "load_config", lambda _path: config())
    monkeypatch.setattr(cli, "run_migrations", lambda _database: None)

    exit_code = cli.main(["--database", str(db_path), "favorites"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "topic-123" in output
    assert "Vendo Acme Target Pro" in output
    assert "active=True" in output


def test_inspect_cli_does_not_expose_full_post_text_or_secrets(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    db_path = migrated_db_path(tmp_path)
    seed_operational_db(db_path)
    monkeypatch.setattr(cli, "load_config", lambda _path: config())
    monkeypatch.setattr(cli, "run_migrations", lambda _database: None)

    exit_code = cli.main(["--database", str(db_path), "inspect", "topic-123"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "topic: id=" in output
    assert "external_topic_id=topic-123" in output
    assert "favorite: id=" in output
    assert "event: id=" in output
    assert "SMTP_PASSWORD" not in output
    assert "env-secret" not in output


def test_favorite_deactivate_and_reactivate_are_reversible_and_emit_events(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    db_path = migrated_db_path(tmp_path)
    seed_operational_db(db_path)
    monkeypatch.setattr(cli, "load_config", lambda _path: config())
    monkeypatch.setattr(cli, "run_migrations", lambda _database: None)

    deactivate_code = cli.main(["--database", str(db_path), "favorite", "deactivate", "topic-123"])
    reactivate_code = cli.main(["--database", str(db_path), "favorite", "reactivate", "topic-123"])

    output = capsys.readouterr().out
    assert deactivate_code == 0
    assert reactivate_code == 0
    assert "favorite deactivated:" in output
    assert "favorite reactivated:" in output

    engine = create_sqlite_engine(db_path)
    factory = session_factory(engine)
    with session_scope(factory) as session:
        favorite = session.query(FavoriteORM).one()
        assert favorite.is_active is True
        assert (
            session.query(FavoriteORM)
            .join(TopicORM)
            .filter(TopicORM.external_topic_id == "topic-123")
            .count()
            == 1
        )
        event_types = {event.event_type for event in favorite.events}
        assert EventType.BECAME_UNAVAILABLE.value in event_types
        assert EventType.FAVORITE_REACTIVATED.value in event_types


def test_favorite_deactivate_is_noop_when_already_inactive(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    db_path = migrated_db_path(tmp_path)
    seed_operational_db(db_path)
    monkeypatch.setattr(cli, "load_config", lambda _path: config())
    monkeypatch.setattr(cli, "run_migrations", lambda _database: None)

    first = cli.main(["--database", str(db_path), "favorite", "deactivate", "topic-123"])
    second = cli.main(["--database", str(db_path), "favorite", "deactivate", "topic-123"])

    output = capsys.readouterr().out
    assert first == 0
    assert second == 0
    assert "favorite already inactive:" in output

    engine = create_sqlite_engine(db_path)
    factory = session_factory(engine)
    with session_scope(factory) as session:
        assert (
            session.query(FavoriteORM)
            .one()
            .events[1]
            .notification_status
            == NotificationStatus.PENDING.value
        )
        assert (
            session.query(FavoriteORM)
            .one()
            .events[1]
            .event_type
            == EventType.BECAME_UNAVAILABLE.value
        )
        assert len(session.query(FavoriteORM).one().events) == 2


def test_backup_cli_creates_consistent_sqlite_copy(monkeypatch, capsys, tmp_path: Path) -> None:
    db_path = migrated_db_path(tmp_path)
    seed_operational_db(db_path)
    backup_path = tmp_path / "backups" / "monitor-backup.db"
    monkeypatch.setattr(cli, "load_config", lambda _path: config())
    monkeypatch.setattr(cli, "run_migrations", lambda _database: None)

    exit_code = cli.main(["--database", str(db_path), "backup", str(backup_path)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert f"backup completed: {backup_path}" in output
    with sqlite3.connect(backup_path) as connection:
        topic_count = connection.execute("SELECT count(*) FROM topics").fetchone()[0]
        favorite_count = connection.execute("SELECT count(*) FROM favorites").fetchone()[0]
    assert topic_count == 1
    assert favorite_count == 1
