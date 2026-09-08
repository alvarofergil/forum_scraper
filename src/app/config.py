"""Configuration loading and validation."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import yaml

from app.models import EventType, WatchItem


class ConfigError(ValueError):
    """Raised when the runtime configuration is missing or invalid."""


SECRET_KEYS = frozenset(
    {
        "smtp_host",
        "smtp_port",
        "smtp_user",
        "smtp_password",
        "notification_email",
    }
)


@dataclass(frozen=True, slots=True)
class SourceConfig:
    """Forum source configuration."""

    type: str
    base_url: str
    forum_id: int


@dataclass(frozen=True, slots=True)
class BootstrapConfig:
    """Initial discovery configuration."""

    pages: int = 10


@dataclass(frozen=True, slots=True)
class DiscoveryConfig:
    """Incremental discovery configuration."""

    overlap_minutes: int = 30
    max_pages_per_run: int = 50


@dataclass(frozen=True, slots=True)
class FavoritesConfig:
    """Favorite monitoring configuration."""

    check_every_run: bool = True
    unavailable_confirmation_runs: int = 2


@dataclass(frozen=True, slots=True)
class ScrapingConfig:
    """Low-impact scraping behavior."""

    request_delay_seconds: float = 2
    timeout_seconds: float = 20
    max_retries: int = 3
    user_agent: str = "PersonalForumMonitor/1.0"


@dataclass(frozen=True, slots=True)
class AiConfig:
    """AI classification configuration."""

    enabled: bool = True
    model: str | None = None
    match_confidence_threshold: float = 0.85


@dataclass(frozen=True, slots=True)
class NotificationsConfig:
    """Notification filtering configuration."""

    email_enabled: bool = True
    notify_event_types: tuple[EventType, ...] = (
        EventType.NEW_FAVORITE,
        EventType.PRICE_CHANGED,
        EventType.STATUS_CHANGED,
        EventType.BECAME_UNAVAILABLE,
    )


@dataclass(frozen=True, slots=True)
class DebugConfig:
    """Debug behavior."""

    save_failed_html: bool = False


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Validated application configuration."""

    source: SourceConfig
    bootstrap: BootstrapConfig
    discovery: DiscoveryConfig
    favorites: FavoritesConfig
    scraping: ScrapingConfig
    ai: AiConfig
    notifications: NotificationsConfig
    debug: DebugConfig
    watchlist: tuple[WatchItem, ...]


@dataclass(frozen=True, slots=True)
class EmailEnvironment:
    """SMTP settings read from environment variables."""

    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    notification_email: str


def load_config(path: str | Path = "config/config.yaml") -> AppConfig:
    """Load and validate YAML configuration from `path`."""

    config_path = Path(path)
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"configuration file not found: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {config_path}: {exc}") from exc

    data = _require_mapping(raw, "config")
    _reject_yaml_secrets(data)

    return AppConfig(
        source=_parse_source(_section(data, "source", required=True)),
        bootstrap=_parse_bootstrap(_section(data, "bootstrap")),
        discovery=_parse_discovery(_section(data, "discovery")),
        favorites=_parse_favorites(_section(data, "favorites")),
        scraping=_parse_scraping(_section(data, "scraping")),
        ai=_parse_ai(_section(data, "ai")),
        notifications=_parse_notifications(_section(data, "notifications")),
        debug=_parse_debug(_section(data, "debug")),
        watchlist=_parse_watchlist(data.get("watchlist")),
    )


def load_email_environment(environ: Mapping[str, str] | None = None) -> EmailEnvironment:
    """Load notification secrets from environment variables only."""

    source = os.environ if environ is None else environ
    return EmailEnvironment(
        smtp_host=_env_string(source, "SMTP_HOST"),
        smtp_port=_env_port(source, "SMTP_PORT"),
        smtp_user=_env_string(source, "SMTP_USER"),
        smtp_password=_env_string(source, "SMTP_PASSWORD"),
        notification_email=_env_string(source, "NOTIFICATION_EMAIL"),
    )


def _parse_source(data: Mapping[str, Any]) -> SourceConfig:
    source_type = _string(data, "type", "source.type")
    if source_type != "armas_es":
        raise ConfigError("source.type must be armas_es")

    return SourceConfig(
        type=source_type,
        base_url=_absolute_http_url(data, "base_url", "source.base_url"),
        forum_id=_positive_int(data.get("forum_id"), "source.forum_id"),
    )


def _parse_bootstrap(data: Mapping[str, Any]) -> BootstrapConfig:
    return BootstrapConfig(pages=_positive_int(data.get("pages", 10), "bootstrap.pages"))


def _parse_discovery(data: Mapping[str, Any]) -> DiscoveryConfig:
    return DiscoveryConfig(
        overlap_minutes=_non_negative_int(
            data.get("overlap_minutes", 30), "discovery.overlap_minutes"
        ),
        max_pages_per_run=_positive_int(
            data.get("max_pages_per_run", 50), "discovery.max_pages_per_run"
        ),
    )


def _parse_favorites(data: Mapping[str, Any]) -> FavoritesConfig:
    return FavoritesConfig(
        check_every_run=_bool(data.get("check_every_run", True), "favorites.check_every_run"),
        unavailable_confirmation_runs=_positive_int(
            data.get("unavailable_confirmation_runs", 2),
            "favorites.unavailable_confirmation_runs",
        ),
    )


def _parse_scraping(data: Mapping[str, Any]) -> ScrapingConfig:
    return ScrapingConfig(
        request_delay_seconds=_non_negative_number(
            data.get("request_delay_seconds", 2), "scraping.request_delay_seconds"
        ),
        timeout_seconds=_positive_number(
            data.get("timeout_seconds", 20), "scraping.timeout_seconds"
        ),
        max_retries=_non_negative_int(data.get("max_retries", 3), "scraping.max_retries"),
        user_agent=_string(
            data,
            "user_agent",
            "scraping.user_agent",
            default="PersonalForumMonitor/1.0",
        ),
    )


def _parse_ai(data: Mapping[str, Any]) -> AiConfig:
    model = data.get("model")
    if model is not None and (not isinstance(model, str) or not model.strip()):
        raise ConfigError("ai.model must be a string or null")
    if isinstance(model, str):
        model = model.strip()

    return AiConfig(
        enabled=_bool(data.get("enabled", True), "ai.enabled"),
        model=model,
        match_confidence_threshold=_confidence(
            data.get("match_confidence_threshold", 0.85),
            "ai.match_confidence_threshold",
        ),
    )


def _parse_notifications(data: Mapping[str, Any]) -> NotificationsConfig:
    raw_events = data.get(
        "notify_event_types",
        [
            EventType.NEW_FAVORITE.value,
            EventType.PRICE_CHANGED.value,
            EventType.STATUS_CHANGED.value,
            EventType.BECAME_UNAVAILABLE.value,
        ],
    )
    if not isinstance(raw_events, list):
        raise ConfigError("notifications.notify_event_types must be a list")

    return NotificationsConfig(
        email_enabled=_bool(data.get("email_enabled", True), "notifications.email_enabled"),
        notify_event_types=tuple(
            _event_type(value, f"notifications.notify_event_types[{index}]")
            for index, value in enumerate(raw_events)
        ),
    )


def _parse_debug(data: Mapping[str, Any]) -> DebugConfig:
    return DebugConfig(
        save_failed_html=_bool(data.get("save_failed_html", False), "debug.save_failed_html")
    )


def _parse_watchlist(value: object) -> tuple[WatchItem, ...]:
    if not isinstance(value, list) or not value:
        raise ConfigError("watchlist must be a non-empty list")

    items: list[WatchItem] = []
    seen_ids: set[str] = set()
    for index, raw_item in enumerate(value):
        item_path = f"watchlist[{index}]"
        item = _require_mapping(raw_item, item_path)
        watch_id = _string(item, "id", f"{item_path}.id")
        if watch_id in seen_ids:
            raise ConfigError(f"{item_path}.id must be unique")
        seen_ids.add(watch_id)

        raw_aliases = item.get("aliases", [])
        if raw_aliases is None:
            raw_aliases = []
        if not isinstance(raw_aliases, list):
            raise ConfigError(f"{item_path}.aliases must be a list")
        aliases = tuple(
            _string_value(alias, f"{item_path}.aliases[{alias_index}]")
            for alias_index, alias in enumerate(raw_aliases)
        )

        items.append(
            WatchItem(
                id=watch_id,
                brand=_string(item, "brand", f"{item_path}.brand"),
                model=_string(item, "model", f"{item_path}.model"),
                aliases=aliases,
            )
        )

    return tuple(items)


def _section(data: Mapping[str, Any], key: str, *, required: bool = False) -> Mapping[str, Any]:
    value = data.get(key)
    if value is None:
        if required:
            raise ConfigError(f"{key} is required")
        return {}
    return _require_mapping(value, key)


def _require_mapping(value: object, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigError(f"{path} must be a mapping")
    return value


def _reject_yaml_secrets(value: object, path: str = "config") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"
            if key_text.lower() in SECRET_KEYS:
                raise ConfigError(f"{child_path}: secrets must come from environment")
            _reject_yaml_secrets(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_yaml_secrets(child, f"{path}[{index}]")


def _string(
    data: Mapping[str, Any],
    key: str,
    path: str,
    *,
    default: str | None = None,
) -> str:
    value = data.get(key, default)
    return _string_value(value, path)


def _string_value(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{path} must be a non-empty string")
    return value.strip()


def _absolute_http_url(data: Mapping[str, Any], key: str, path: str) -> str:
    value = _string(data, key, path)
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ConfigError(f"{path} must be an absolute HTTP(S) URL")
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def _bool(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{path} must be a boolean")
    return value


def _positive_int(value: object, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigError(f"{path} must be a positive integer")
    return value


def _non_negative_int(value: object, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ConfigError(f"{path} must be a non-negative integer")
    return value


def _positive_number(value: object, path: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool) or value <= 0:
        raise ConfigError(f"{path} must be a positive number")
    return float(value)


def _non_negative_number(value: object, path: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool) or value < 0:
        raise ConfigError(f"{path} must be a non-negative number")
    return float(value)


def _confidence(value: object, path: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ConfigError(f"{path} must be a number")
    confidence = float(value)
    if confidence < 0 or confidence > 1:
        raise ConfigError(f"{path} must be between 0 and 1")
    return confidence


def _event_type(value: object, path: str) -> EventType:
    if not isinstance(value, str):
        raise ConfigError(f"{path} must be an event type string")
    try:
        return EventType(value.strip().upper())
    except ValueError as exc:
        raise ConfigError(f"{path} has unknown event type: {value}") from exc


def _env_string(environ: Mapping[str, str], key: str) -> str:
    value = environ.get(key)
    if value is None or not value.strip():
        raise ConfigError(f"{key} environment variable is required")
    return value.strip()


def _env_port(environ: Mapping[str, str], key: str) -> int:
    raw_value = _env_string(environ, key)
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigError(f"{key} must be a positive integer") from exc
    return _positive_int(value, key)
