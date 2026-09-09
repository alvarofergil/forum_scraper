from __future__ import annotations

from app import cli
from app.config import (
    AiConfig,
    AppConfig,
    BootstrapConfig,
    ConfigError,
    DebugConfig,
    DiscoveryConfig,
    EmailEnvironment,
    FavoritesConfig,
    NotificationsConfig,
    ScrapingConfig,
    SourceConfig,
)
from app.models import EventType, WatchItem
from discovery.service import BootstrapResult, RunResult
from notifications.email import NotificationRetryResult


class FakeDiscoveryService:
    last_force: bool | None = None

    def __init__(self, **_kwargs: object) -> None:
        pass

    def bootstrap(self, *, force: bool = False) -> BootstrapResult:
        FakeDiscoveryService.last_force = force
        return BootstrapResult(
            pages_seen=1,
            topics_seen=2,
            candidates_seen=1,
            pending_candidates=0,
            classified_candidates=1,
            discarded_candidates=0,
            favorites_created=1,
        )

    def run_once(self) -> RunResult:
        return RunResult(
            discovery_pages_seen=1,
            discovery_topics_seen=2,
            discovery_candidates_seen=1,
            discovery_completed=True,
            discovery_limit_reached=False,
            pending_candidates_checked=0,
            pending_candidates_classified=0,
            pending_candidates_discarded=0,
            pending_candidates_failed=0,
            pending_candidates_remaining=0,
            pending_candidates_completed=True,
            pending_candidates_skipped=False,
            favorites_checked=1,
            favorites_unchanged=1,
            favorites_changed=0,
            favorites_changed_unclassified=0,
            favorites_check_errors=0,
            favorites_check_completed=True,
            favorites_check_skipped=False,
        )


class FakeEmailNotificationService:
    def __init__(self, **_kwargs: object) -> None:
        pass

    def retry_pending_and_failed(self) -> NotificationRetryResult:
        return NotificationRetryResult(sent=2, failed=1, skipped=3)


def config(
    *,
    email_enabled: bool = True,
    notify_event_types: tuple[EventType, ...] | None = None,
) -> AppConfig:
    return AppConfig(
        source=SourceConfig(type="armas_es", base_url="https://www.armas.es", forum_id=96),
        bootstrap=BootstrapConfig(pages=1),
        discovery=DiscoveryConfig(),
        favorites=FavoritesConfig(),
        scraping=ScrapingConfig(request_delay_seconds=0),
        ai=AiConfig(enabled=False),
        notifications=NotificationsConfig(
            email_enabled=email_enabled,
            notify_event_types=notify_event_types
            if notify_event_types is not None
            else NotificationsConfig().notify_event_types,
        ),
        debug=DebugConfig(),
        watchlist=(WatchItem(id="watch-001", brand="Acme", model="Target Pro"),),
    )


def test_bootstrap_cli_uses_force_and_prints_summary(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    monkeypatch.setattr(cli, "load_config", lambda _path: config())
    monkeypatch.setattr(cli, "run_migrations", lambda _database: None)
    monkeypatch.setattr(cli, "create_sqlite_engine", lambda _database: object())
    monkeypatch.setattr(cli, "session_factory", lambda _engine: object())
    monkeypatch.setattr(cli, "ArmasEsClient", _FakeClientFactory)
    monkeypatch.setattr(cli, "ArmasEsTopicFetcher", lambda **_kwargs: object())
    monkeypatch.setattr(cli, "DiscoveryService", FakeDiscoveryService)

    exit_code = cli.main(
        [
            "--config",
            str(tmp_path / "config.yaml"),
            "--database",
            str(tmp_path / "monitor.db"),
            "bootstrap",
            "--force",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert FakeDiscoveryService.last_force is True
    assert "bootstrap completed: pages=1 topics=2 candidates=1 favorites=1 pending=0" in output


def test_run_cli_prints_single_pass_summary(monkeypatch, capsys, tmp_path) -> None:
    monkeypatch.setattr(cli, "load_config", lambda _path: config(email_enabled=False))
    monkeypatch.setattr(
        cli,
        "load_email_environment",
        lambda: (_ for _ in ()).throw(AssertionError("email env not required")),
    )
    monkeypatch.setattr(cli, "run_migrations", lambda _database: None)
    monkeypatch.setattr(cli, "_discovery_service", lambda _config, database: FakeDiscoveryService())

    exit_code = cli.main(
        [
            "--config",
            str(tmp_path / "config.yaml"),
            "--database",
            str(tmp_path / "monitor.db"),
            "run",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert (
        "run completed: discovery_pages=1 discovery_topics=2 discovery_candidates=1 "
        "discovery_completed=True discovery_limit_reached=False "
        "pending_checked=0 pending_classified=0 pending_discarded=0 "
        "pending_failed=0 pending_remaining=0 pending_completed=True "
        "pending_skipped=False favorites_checked=1 favorites_unchanged=1 "
        "favorites_changed=0 favorites_changed_unclassified=0 "
        "favorites_check_errors=0 favorites_check_completed=True "
        "favorites_check_skipped=False notifications_skipped=email_disabled"
    ) in output


def test_run_cli_sends_configured_notifications(monkeypatch, capsys, tmp_path) -> None:
    monkeypatch.setattr(cli, "load_config", lambda _path: config(email_enabled=True))
    monkeypatch.setattr(
        cli,
        "load_email_environment",
        lambda: EmailEnvironment(
            smtp_host="smtp.example.test",
            smtp_port=587,
            smtp_user="sender@example.test",
            smtp_password="env-secret",
            notification_email="recipient@example.test",
        ),
    )
    monkeypatch.setattr(cli, "run_migrations", lambda _database: None)
    monkeypatch.setattr(cli, "_discovery_service", lambda _config, database: FakeDiscoveryService())
    monkeypatch.setattr(cli, "create_sqlite_engine", lambda _database: object())
    monkeypatch.setattr(cli, "session_factory", lambda _engine: _SessionFactory())
    monkeypatch.setattr(cli, "EmailNotificationService", FakeEmailNotificationService)

    exit_code = cli.main(
        [
            "--config",
            str(tmp_path / "config.yaml"),
            "--database",
            str(tmp_path / "monitor.db"),
            "run",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "notifications_sent=2 notifications_failed=1 notifications_skipped=3" in output
    assert "env-secret" not in output


def test_run_cli_reports_missing_smtp_environment(monkeypatch, capsys, tmp_path) -> None:
    monkeypatch.setattr(cli, "load_config", lambda _path: config(email_enabled=True))
    monkeypatch.setattr(
        cli,
        "load_email_environment",
        lambda: (_ for _ in ()).throw(ConfigError("missing environment variable: SMTP_HOST")),
    )
    monkeypatch.setattr(cli, "run_migrations", lambda _database: None)
    monkeypatch.setattr(cli, "_discovery_service", lambda _config, database: FakeDiscoveryService())

    exit_code = cli.main(
        [
            "--config",
            str(tmp_path / "config.yaml"),
            "--database",
            str(tmp_path / "monitor.db"),
            "run",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "notifications_sent=0 notifications_failed=configuration_error" in output
    assert "SMTP_HOST" in output
    assert "SMTP_PASSWORD" not in output
    assert "env-secret" not in output


def test_retry_notifications_cli_prints_delivery_summary(monkeypatch, capsys, tmp_path) -> None:
    monkeypatch.setattr(cli, "load_config", lambda _path: config())
    monkeypatch.setattr(cli, "load_email_environment", lambda: object())
    monkeypatch.setattr(cli, "run_migrations", lambda _database: None)
    monkeypatch.setattr(cli, "create_sqlite_engine", lambda _database: object())
    monkeypatch.setattr(cli, "session_factory", lambda _engine: _SessionFactory())
    monkeypatch.setattr(cli, "EmailNotificationService", FakeEmailNotificationService)

    exit_code = cli.main(
        [
            "--config",
            str(tmp_path / "config.yaml"),
            "--database",
            str(tmp_path / "monitor.db"),
            "retry-notifications",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "retry-notifications completed: sent=2 failed=1 skipped=3" in output


class _FakeClientFactory:
    @classmethod
    def from_scraping_config(cls, *_args: object, **_kwargs: object) -> object:
        return object()


class _SessionFactory:
    def __call__(self) -> _FakeSession:
        return _FakeSession()


class _FakeSession:
    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None
