"""Pure URL helpers for the armas.es phpBB forum."""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit

DEFAULT_BASE_URL = "https://www.armas.es"
DEFAULT_FORUM_ID = 96
FORUM_PATH = "/foros/"
TOPIC_PATH = "/foros/viewtopic.php"


class ArmasUrlError(ValueError):
    """Raised when an armas.es URL cannot provide the required identity."""


def resolve_forum_url(url: str, *, base_url: str = DEFAULT_BASE_URL) -> str:
    """Resolve an armas.es forum URL against the configured base URL."""

    base = _normalized_base(base_url)
    return urljoin(base, _require_url(url))


def extract_topic_id(url: str, *, base_url: str = DEFAULT_BASE_URL) -> str:
    """Extract the phpBB topic identity from query parameter `t`."""

    resolved_url = resolve_forum_url(url, base_url=base_url)
    _require_same_host(resolved_url, base_url)
    query = parse_qs(urlsplit(resolved_url).query, keep_blank_values=True)
    topic_ids = query.get("t", [])
    topic_id = topic_ids[0].strip() if topic_ids else ""
    if not topic_id:
        raise ArmasUrlError("missing topic id parameter: t")
    return topic_id


def canonical_topic_url(
    topic_id: str | int,
    *,
    base_url: str = DEFAULT_BASE_URL,
    forum_id: int = DEFAULT_FORUM_ID,
) -> str:
    """Build the canonical topic URL stored by the application."""

    normalized_topic_id = str(topic_id).strip()
    if not normalized_topic_id:
        raise ArmasUrlError("missing topic id")
    if forum_id <= 0:
        raise ArmasUrlError("forum_id must be positive")

    base = urlsplit(_normalized_base(base_url))
    query = urlencode({"f": forum_id, "t": normalized_topic_id})
    return urlunsplit((base.scheme, base.netloc, TOPIC_PATH, query, ""))


def normalize_topic_url(
    url: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    forum_id: int = DEFAULT_FORUM_ID,
) -> str:
    """Resolve a topic URL and return its canonical identity URL."""

    topic_id = extract_topic_id(url, base_url=base_url)
    return canonical_topic_url(topic_id, base_url=base_url, forum_id=forum_id)


def _normalized_base(base_url: str) -> str:
    value = _require_url(base_url).rstrip("/")
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ArmasUrlError("base_url must be an absolute HTTP(S) URL")
    return f"{value}{FORUM_PATH}"


def _require_same_host(url: str, base_url: str) -> None:
    url_host = urlsplit(url).netloc.lower()
    base_host = urlsplit(_require_url(base_url)).netloc.lower()
    if url_host != base_host:
        raise ArmasUrlError("topic URL host must match configured base_url")


def _require_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise ArmasUrlError("url must be a non-empty string")
    return url.strip()
