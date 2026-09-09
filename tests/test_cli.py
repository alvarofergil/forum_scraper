from __future__ import annotations

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
from app.models import WatchItem
from discovery.service import BootstrapResult, RunResult


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
            favorites_checked=1,
            favorites_changed=0,
        )


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
    monkeypatch.setattr(cli, "load_config", lambda _path: config())
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
        "discovery_completed=True favorites_checked=1 favorites_changed=0"
    ) in output


class _FakeClientFactory:
    @classmethod
    def from_scraping_config(cls, *_args: object, **_kwargs: object) -> object:
        return object()
