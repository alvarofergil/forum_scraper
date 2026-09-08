"""Command line entrypoints for Forum Scraper."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.config import AppConfig, load_config
from classification.openai_classifier import OpenAIClassifier
from discovery.service import BootstrapAlreadyCompletedError, DiscoveryService
from sources.armas_es.client import ArmasEsClient
from sources.armas_es.listing_parser import parse_listing_page
from sources.armas_es.topic_fetcher import ArmasEsTopicFetcher
from storage import create_sqlite_engine, run_migrations, session_factory


def main(argv: list[str] | None = None) -> int:
    """Run the Forum Scraper CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)

    if args.command == "bootstrap":
        return _bootstrap(config, database=args.database, force=args.force)
    if args.command == "debug-listing":
        return _debug_listing(config)

    parser.error("unknown command")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--database", default="data/monitor.db")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap")
    bootstrap.add_argument("--force", action="store_true")

    subparsers.add_parser("debug-listing")
    return parser


def _bootstrap(config: AppConfig, *, database: str | Path, force: bool) -> int:
    run_migrations(database)
    engine = create_sqlite_engine(database)
    factory = session_factory(engine)
    client = ArmasEsClient.from_scraping_config(
        config.scraping,
        base_url=config.source.base_url,
        forum_id=config.source.forum_id,
    )
    service = DiscoveryService(
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
