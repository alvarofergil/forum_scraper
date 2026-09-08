"""Pure URL helpers for the armas.es phpBB forum."""

from __future__ import annotations

from urllib.parse import parse_qs, parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

DEFAULT_BASE_URL = "https://www.armas.es"
DEFAULT_FORUM_ID = 96
FORUM_PATH = "/foros/"
LISTING_PATH = "/foros/viewforum.php"
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


def canonical_topic_page_url(
    topic_id: str | int,
    *,
    start: int = 0,
    base_url: str = DEFAULT_BASE_URL,
    forum_id: int = DEFAULT_FORUM_ID,
) -> str:
    """Build a canonical topic URL for a specific phpBB pagination offset."""

    if start < 0:
        raise ArmasUrlError("start must be non-negative")
    normalized_topic_id = str(topic_id).strip()
    if not normalized_topic_id:
        raise ArmasUrlError("missing topic id")
    if forum_id <= 0:
        raise ArmasUrlError("forum_id must be positive")

    query: dict[str, str | int] = {"f": forum_id, "t": normalized_topic_id}
    if start:
        query["start"] = start

    base = urlsplit(_normalized_base(base_url))
    return urlunsplit((base.scheme, base.netloc, TOPIC_PATH, urlencode(query), ""))


def normalize_topic_url(
    url: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    forum_id: int = DEFAULT_FORUM_ID,
) -> str:
    """Resolve a topic URL and return its canonical identity URL."""

    topic_id = extract_topic_id(url, base_url=base_url)
    return canonical_topic_url(topic_id, base_url=base_url, forum_id=forum_id)


def normalize_listing_page_url(
    url: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    forum_id: int = DEFAULT_FORUM_ID,
) -> str | None:
    """Resolve and canonicalize a listing pagination URL when it stays in scope."""

    resolved_url = resolve_forum_url(url, base_url=base_url)
    if not _has_same_host(resolved_url, base_url):
        return None

    parts = urlsplit(resolved_url)
    if parts.path != LISTING_PATH:
        return None

    query_values = parse_qsl(parts.query, keep_blank_values=True)
    forum_ids = [value for key, value in query_values if key == "f"]
    if forum_ids != [str(forum_id)]:
        return None

    canonical_query = [("f", str(forum_id))]
    start_values = [value for key, value in query_values if key == "start"]
    if start_values:
        if len(start_values) != 1:
            return None
        try:
            start = int(start_values[0])
        except ValueError:
            return None
        if start < 0:
            return None
        canonical_query.append(("start", str(start)))

    base = urlsplit(_normalized_base(base_url))
    return urlunsplit((base.scheme, base.netloc, LISTING_PATH, urlencode(canonical_query), ""))


def _normalized_base(base_url: str) -> str:
    value = _require_url(base_url).rstrip("/")
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ArmasUrlError("base_url must be an absolute HTTP(S) URL")
    return f"{value}{FORUM_PATH}"


def _require_same_host(url: str, base_url: str) -> None:
    if not _has_same_host(url, base_url):
        raise ArmasUrlError("topic URL host must match configured base_url")


def _has_same_host(url: str, base_url: str) -> bool:
    url_host = urlsplit(url).netloc.lower()
    base_host = urlsplit(_require_url(base_url)).netloc.lower()
    return url_host == base_host


def _require_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise ArmasUrlError("url must be a non-empty string")
    return url.strip()
