"""Command line entrypoints for Forum Scraper."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.config import AppConfig, ConfigError, load_config, load_email_environment
from app.models import EventType, utc_now
from classification.openai_classifier import OpenAIClassifier
from discovery.service import BootstrapAlreadyCompletedError, DiscoveryService
from notifications.email import EmailNotificationService, NotificationRetryResult
from sources.armas_es.client import ArmasEsClient
from sources.armas_es.listing_parser import parse_listing_page
from sources.armas_es.topic_fetcher import ArmasEsTopicFetcher
from storage import (
    create_sqlite_engine,
    run_migrations,
    session_factory,
    session_scope,
)
from storage.operational import (
    backup_sqlite_database,
    deactivate_favorite,
    inspect_topic,
    list_favorites,
    reactivate_favorite,
    read_status,
)


def main(argv: list[str] | None = None) -> int:
    """Run the Forum Scraper CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    config_path = args.config or "config/config.yaml"
    config = (
        load_config(config_path)
        if args.command in {"bootstrap", "run", "retry-notifications", "debug-listing"}
        else None
    )

    if args.command == "bootstrap":
        assert config is not None
        return _bootstrap(config, database=args.database, force=args.force)
    if args.command == "run":
        assert config is not None
        return _run(config, database=args.database)
    if args.command == "retry-notifications":
        assert config is not None
        return _retry_notifications(config, database=args.database)
    if args.command == "status":
        return _status(database=args.database, config_path=args.config)
    if args.command == "favorites":
        return _favorites(database=args.database)
    if args.command == "inspect":
        return _inspect(database=args.database, topic_identifier=args.topic_id)
    if args.command == "favorite":
        return _favorite_action(
            database=args.database,
            action=args.favorite_action,
            topic_identifier=args.topic_id,
        )
    if args.command == "backup":
        return _backup(database=args.database, destination=args.destination)
    if args.command == "debug-listing":
        assert config is not None
        return _debug_listing(config)

    parser.error("unknown command")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app")
    parser.add_argument("--config")
    parser.add_argument("--database", default="data/monitor.db")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap", help="run bounded initial discovery")
    bootstrap.add_argument("--force", action="store_true")

    subparsers.add_parser("run", help="run one incremental monitor pass")
    subparsers.add_parser("retry-notifications", help="retry pending and failed emails")
    subparsers.add_parser("status", help="print database status summary")
    subparsers.add_parser("favorites", help="list monitored favorites")

    inspect = subparsers.add_parser("inspect", help="inspect safe topic metadata")
    inspect.add_argument("topic_id")

    favorite = subparsers.add_parser("favorite", help="manage one favorite by topic id")
    favorite_subparsers = favorite.add_subparsers(dest="favorite_action", required=True)
    for action in ("deactivate", "reactivate"):
        favorite_action = favorite_subparsers.add_parser(action)
        favorite_action.add_argument("topic_id")

    backup = subparsers.add_parser("backup", help="create a consistent SQLite backup")
    backup.add_argument("destination", nargs="?")

    subparsers.add_parser("debug-listing", help="print parsed listing rows")
    return parser


def _bootstrap(config: AppConfig, *, database: str | Path, force: bool) -> int:
    run_migrations(database)
    service = _discovery_service(config, database=database)
    try:
        result = service.bootstrap(force=force)
    except BootstrapAlreadyCompletedError as exc:
        print(exc)
        return 1

    print(
        "bootstrap completed: "
        f"pages={result.pages_seen} topics={result.topics_seen} "
        f"candidates={result.candidates_seen} favorites={result.favorites_created} "
        f"pending={result.pending_candidates}"
    )
    return 0


def _run(config: AppConfig, *, database: str | Path) -> int:
    run_migrations(database)
    service = _discovery_service(config, database=database)
    result = service.run_once()
    notification_summary = "notifications_skipped=email_disabled"
    exit_code = 0
    if config.notifications.email_enabled:
        try:
            notification_result = _send_notifications(config, database=database)
        except ConfigError as exc:
            notification_summary = (
                "notifications_sent=0 notifications_failed=configuration_error "
                "notifications_skipped=0"
            )
            print(f"notifications error: {exc}")
            exit_code = 1
        else:
            notification_summary = (
                f"notifications_sent={notification_result.sent} "
                f"notifications_failed={notification_result.failed} "
                f"notifications_skipped={notification_result.skipped}"
            )
    print(
        "run completed: "
        f"discovery_pages={result.discovery_pages_seen} "
        f"discovery_topics={result.discovery_topics_seen} "
        f"discovery_candidates={result.discovery_candidates_seen} "
        f"discovery_completed={result.discovery_completed} "
        f"discovery_limit_reached={result.discovery_limit_reached} "
        f"pending_checked={result.pending_candidates_checked} "
        f"pending_classified={result.pending_candidates_classified} "
        f"pending_discarded={result.pending_candidates_discarded} "
        f"pending_failed={result.pending_candidates_failed} "
        f"pending_remaining={result.pending_candidates_remaining} "
        f"pending_completed={result.pending_candidates_completed} "
        f"pending_skipped={result.pending_candidates_skipped} "
        f"favorites_checked={result.favorites_checked} "
        f"favorites_changed={result.favorites_changed} "
        f"favorites_check_errors={result.favorites_check_errors} "
        f"favorites_check_completed={result.favorites_check_completed} "
        f"favorites_check_skipped={result.favorites_check_skipped} "
        f"{notification_summary}"
    )
    return exit_code


def _retry_notifications(config: AppConfig, *, database: str | Path) -> int:
    if not config.notifications.email_enabled:
        print("retry-notifications skipped: email_enabled=False")
        return 0

    run_migrations(database)
    engine = create_sqlite_engine(database)
    factory = session_factory(engine)
    with session_scope(factory) as session:
        result = EmailNotificationService(
            session=session,
            email_environment=load_email_environment(),
            notifications=config.notifications,
        ).retry_pending_and_failed()

    print(
        "retry-notifications completed: "
        f"sent={result.sent} failed={result.failed} skipped={result.skipped}"
    )
    return 0


def _send_notifications(config: AppConfig, *, database: str | Path) -> NotificationRetryResult:
    engine = create_sqlite_engine(database)
    factory = session_factory(engine)
    with session_scope(factory) as session:
        return EmailNotificationService(
            session=session,
            email_environment=load_email_environment(),
            notifications=config.notifications,
        ).retry_pending_and_failed()


def _status(*, database: str | Path, config_path: str | None) -> int:
    run_migrations(database)
    notify_event_types = _status_notify_event_types(config_path)
    engine = create_sqlite_engine(database)
    factory = session_factory(engine)
    with session_scope(factory) as session:
        status = read_status(session, notify_event_types=notify_event_types)

    print(
        "status: "
        f"topics={status.topics} favorites={status.favorites} "
        f"active_favorites={status.active_favorites} "
        f"inactive_favorites={status.inactive_favorites} "
        f"pending_candidates={status.pending_candidates} "
        f"events_pending={status.events_pending} events_failed={status.events_failed} "
        f"events_sent={status.events_sent} "
        f"events_pending_non_notifiable={status.events_pending_non_notifiable} "
        f"events_failed_non_notifiable={status.events_failed_non_notifiable}"
    )
    for key, value in status.state:
        print(f"state: {key}={value}")
    return 0


def _favorites(*, database: str | Path) -> int:
    run_migrations(database)
    engine = create_sqlite_engine(database)
    factory = session_factory(engine)
    with session_scope(factory) as session:
        favorites = list_favorites(session)

    for favorite in favorites:
        print(
            f"favorite: id={favorite.id} topic={favorite.topic_external_id} "
            f"watch_item={favorite.watch_item_id} status={favorite.status} "
            f"active={favorite.is_active} price={favorite.current_price} "
            f"currency={favorite.currency} title={favorite.title} "
            f"url={favorite.canonical_url}"
        )
    if not favorites:
        print("favorites: none")
    return 0


def _inspect(*, database: str | Path, topic_identifier: str) -> int:
    run_migrations(database)
    engine = create_sqlite_engine(database)
    factory = session_factory(engine)
    with session_scope(factory) as session:
        inspection = inspect_topic(session, topic_identifier)
        if inspection is None:
            print(f"inspect failed: topic not found: {topic_identifier}")
            return 1

        topic = inspection.topic
        print(
            f"topic: id={topic.id} external_topic_id={topic.external_topic_id} "
            f"title={topic.title} author={topic.author or '-'} url={topic.canonical_url}"
        )
        if inspection.favorite is None:
            print("favorite: none")
        else:
            favorite = inspection.favorite
            print(
                f"favorite: id={favorite.id} watch_item={favorite.watch_item_id} "
                f"status={favorite.status} active={favorite.is_active} "
                f"price={favorite.current_price if favorite.current_price is not None else '-'} "
                f"currency={favorite.currency or '-'}"
            )
        for event in inspection.events:
            print(
                f"event: id={event.id} type={event.event_type} "
                f"notification_status={event.notification_status} "
                f"created_at={event.created_at.isoformat()}"
            )
    return 0


def _favorite_action(*, database: str | Path, action: str, topic_identifier: str) -> int:
    run_migrations(database)
    engine = create_sqlite_engine(database)
    factory = session_factory(engine)
    with session_scope(factory) as session:
        if action == "deactivate":
            result = deactivate_favorite(session, topic_identifier)
            action_name = "deactivated"
            noop_name = "already inactive"
        else:
            result = reactivate_favorite(session, topic_identifier)
            action_name = "reactivated"
            noop_name = "already active"

        if result is None:
            print(f"favorite {action} failed: topic not found: {topic_identifier}")
            return 1
        if result.changed:
            print(f"favorite {action_name}: id={result.favorite.id} topic={topic_identifier}")
        else:
            print(f"favorite {noop_name}: id={result.favorite.id} topic={topic_identifier}")
    return 0


def _backup(*, database: str | Path, destination: str | Path | None) -> int:
    run_migrations(database)
    backup_path = backup_sqlite_database(
        database,
        destination if destination is not None else _default_backup_destination(),
    )
    print(f"backup completed: {backup_path}")
    return 0


def _status_notify_event_types(config_path: str | None) -> tuple[EventType, ...] | None:
    if config_path is None:
        return None
    return load_config(config_path).notifications.notify_event_types


def _default_backup_destination() -> Path:
    timestamp = utc_now().strftime("%Y%m%d-%H%M%S")
    base = Path("backups") / f"monitor-{timestamp}.db"
    if not base.exists():
        return base

    suffix = 1
    while True:
        candidate = Path("backups") / f"monitor-{timestamp}-{suffix}.db"
        if not candidate.exists():
            return candidate
        suffix += 1


def _discovery_service(config: AppConfig, *, database: str | Path) -> DiscoveryService:
    engine = create_sqlite_engine(database)
    factory = session_factory(engine)
    client = ArmasEsClient.from_scraping_config(
        config.scraping,
        base_url=config.source.base_url,
        forum_id=config.source.forum_id,
    )
    return DiscoveryService(
        config=config,
        session_factory=factory,
        listing_client=client,
        topic_fetcher=ArmasEsTopicFetcher(
            client=client,
            base_url=config.source.base_url,
            forum_id=config.source.forum_id,
        ),
        classifier=OpenAIClassifier.from_config(config.ai) if config.ai.enabled else None,
    )


def _debug_listing(config: AppConfig) -> int:
    client = ArmasEsClient.from_scraping_config(
        config.scraping,
        base_url=config.source.base_url,
        forum_id=config.source.forum_id,
    )
    response = client.get_listing_page(start=0)
    parsed = parse_listing_page(
        response.text,
        base_url=config.source.base_url,
        forum_id=config.source.forum_id,
        current_start=0,
    )
    for topic in parsed.topics:
        print(f"{topic.external_topic_id}\t{topic.title}\t{topic.canonical_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
