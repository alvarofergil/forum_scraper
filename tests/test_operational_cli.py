from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
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
    EmailEnvironment,
    FavoritesConfig,
    NotificationsConfig,
    ScrapingConfig,
    SourceConfig,
)
from app.models import AvailabilityStatus, EventType, NotificationStatus, WatchItem
from events.service import EventService
from notifications.email import EmailNotificationService
from storage import create_sqlite_engine, session_factory, session_scope
from storage.orm import EventORM, FavoriteORM, TopicORM


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


def notifications_config(*event_types: EventType) -> AppConfig:
    base = config()
    return AppConfig(
        source=base.source,
        bootstrap=base.bootstrap,
        discovery=base.discovery,
        favorites=base.favorites,
        scraping=base.scraping,
        ai=base.ai,
        notifications=NotificationsConfig(notify_event_types=event_types),
        debug=base.debug,
        watchlist=base.watchlist,
    )


def fail_load_config(_path: str) -> AppConfig:
    raise AssertionError("config not required")


class FakeSMTP:
    sent_messages: list[str] = []
    fail_send: bool = False

    def __init__(self, _host: str, _port: int, *, timeout: float) -> None:
        self.timeout = timeout

    def __enter__(self) -> FakeSMTP:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def starttls(self) -> None:
        return None

    def login(self, _user: str, _password: str) -> None:
        return None

    def sendmail(self, _sender: str, _recipients: list[str], message: str) -> None:
        if self.fail_send:
            raise OSError("smtp unavailable")
        self.sent_messages.append(message)


def email_environment() -> EmailEnvironment:
    return EmailEnvironment(
        smtp_host="smtp.example.test",
        smtp_port=587,
        smtp_user="sender@example.test",
        smtp_password="env-secret",
        notification_email="recipient@example.test",
    )


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


class FakeRunDiscoveryService:
    def run_once(self):  # type: ignore[no-untyped-def]
        from discovery.service import RunResult

        return RunResult(
            discovery_pages_seen=0,
            discovery_topics_seen=0,
            discovery_candidates_seen=0,
            discovery_completed=True,
            discovery_limit_reached=False,
            pending_candidates_checked=2,
            pending_candidates_classified=1,
            pending_candidates_discarded=0,
            pending_candidates_failed=1,
            pending_candidates_remaining=1,
            pending_candidates_completed=False,
            pending_candidates_skipped=False,
            favorites_checked=0,
            favorites_unchanged=0,
            favorites_changed=0,
            favorites_changed_unclassified=0,
            favorites_check_errors=1,
            favorites_check_completed=True,
            favorites_check_skipped=False,
        )


def fake_email_service(**kwargs: object) -> EmailNotificationService:
    return EmailNotificationService(
        session=kwargs["session"],
        email_environment=kwargs["email_environment"],
        notifications=kwargs["notifications"],
        smtp_factory=FakeSMTP,
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


def test_status_cli_counts_only_configured_pending_events_as_actionable(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    db_path = migrated_db_path(tmp_path)
    seed_operational_db(db_path)
    monkeypatch.setattr(
        cli,
        "load_config",
        lambda _path: notifications_config(EventType.PRICE_CHANGED),
    )
    monkeypatch.setattr(cli, "run_migrations", lambda _database: None)

    exit_code = cli.main(
        ["--config", str(tmp_path / "config.yaml"), "--database", str(db_path), "status"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "events_pending=0" in output
    assert "events_pending_non_notifiable=1" in output


def test_run_cli_sends_pending_events_with_fake_smtp(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    FakeSMTP.sent_messages = []
    FakeSMTP.fail_send = False
    db_path = migrated_db_path(tmp_path)
    seed_operational_db(db_path)
    monkeypatch.setattr(cli, "load_config", lambda _path: config())
    monkeypatch.setattr(cli, "load_email_environment", email_environment)
    monkeypatch.setattr(cli, "run_migrations", lambda _database: None)
    monkeypatch.setattr(
        cli,
        "_discovery_service",
        lambda _config, database: FakeRunDiscoveryService(),
    )
    monkeypatch.setattr(cli, "EmailNotificationService", fake_email_service)

    exit_code = cli.main(["--database", str(db_path), "run"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "pending_checked=2 pending_classified=1" in output
    assert "pending_failed=1 pending_remaining=1 pending_completed=False" in output
    assert "favorites_check_errors=1" in output
    assert "notifications_sent=1 notifications_failed=0 notifications_skipped=0" in output
    assert "env-secret" not in output
    with session_scope(session_factory(create_sqlite_engine(db_path))) as session:
        event = session.query(EventORM).one()
        assert event.notification_status == NotificationStatus.SENT.value
        assert event.notified_at is not None
        assert event.error_message is None
    assert len(FakeSMTP.sent_messages) == 1


def test_run_cli_leaves_smtp_failures_retryable(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    FakeSMTP.sent_messages = []
    FakeSMTP.fail_send = True
    db_path = migrated_db_path(tmp_path)
    seed_operational_db(db_path)
    monkeypatch.setattr(cli, "load_config", lambda _path: config())
    monkeypatch.setattr(cli, "load_email_environment", email_environment)
    monkeypatch.setattr(cli, "run_migrations", lambda _database: None)
    monkeypatch.setattr(
        cli,
        "_discovery_service",
        lambda _config, database: FakeRunDiscoveryService(),
    )
    monkeypatch.setattr(cli, "EmailNotificationService", fake_email_service)

    exit_code = cli.main(["--database", str(db_path), "run"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "notifications_sent=0 notifications_failed=1 notifications_skipped=0" in output
    assert "smtp unavailable" not in output
    with session_scope(session_factory(create_sqlite_engine(db_path))) as session:
        event = session.query(EventORM).one()
        assert event.notification_status == NotificationStatus.FAILED.value
        assert event.notified_at is None
        assert event.error_message == "smtp unavailable"


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


def test_backup_cli_without_destination_uses_timestamped_default(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    db_path = migrated_db_path(tmp_path)
    seed_operational_db(db_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "load_config", lambda _path: config())
    monkeypatch.setattr(cli, "run_migrations", lambda _database: None)
    monkeypatch.setattr(
        cli,
        "utc_now",
        lambda: datetime(2026, 9, 9, 12, 34, 56, tzinfo=UTC),
    )

    exit_code = cli.main(["--database", str(db_path), "backup"])

    backup_path = tmp_path / "backups" / "monitor-20260909-123456.db"
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "backup completed: backups/monitor-20260909-123456.db" in output
    assert backup_path.exists()
    assert not (tmp_path / "backups" / "monitor.db").exists()


def test_backup_cli_without_destination_does_not_overwrite_same_second(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    db_path = migrated_db_path(tmp_path)
    seed_operational_db(db_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "load_config", lambda _path: config())
    monkeypatch.setattr(cli, "run_migrations", lambda _database: None)
    monkeypatch.setattr(
        cli,
        "utc_now",
        lambda: datetime(2026, 9, 9, 12, 34, 56, tzinfo=UTC),
    )

    first = cli.main(["--database", str(db_path), "backup"])
    second = cli.main(["--database", str(db_path), "backup"])

    output = capsys.readouterr().out
    first_path = tmp_path / "backups" / "monitor-20260909-123456.db"
    second_path = tmp_path / "backups" / "monitor-20260909-123456-1.db"
    assert first == 0
    assert second == 0
    assert "backup completed: backups/monitor-20260909-123456.db" in output
    assert "backup completed: backups/monitor-20260909-123456-1.db" in output
    assert first_path.exists()
    assert second_path.exists()
