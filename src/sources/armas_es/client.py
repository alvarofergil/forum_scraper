"""Respectful sequential HTTP client for armas.es."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from app.config import ScrapingConfig
from sources.armas_es.urls import DEFAULT_BASE_URL, DEFAULT_FORUM_ID, canonical_topic_url

TRANSIENT_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})
BLOCKING_STATUS_CODES = frozenset({401, 403})


@dataclass(frozen=True, slots=True)
class ArmasHttpResponse:
    """HTTP response body and metadata needed by downstream parsers."""

    status_code: int
    text: str
    final_url: str


class ArmasHttpClientError(RuntimeError):
    """Base error raised by the armas.es HTTP client."""


class ArmasHttpStatusError(ArmasHttpClientError):
    """Raised for non-success HTTP status codes."""

    def __init__(self, status_code: int, url: str) -> None:
        super().__init__(f"HTTP {status_code} while requesting {url}")
        self.status_code = status_code
        self.url = url


class ArmasBlockedError(ArmasHttpStatusError):
    """Raised when the site returns an explicit blocking/authorization status."""

    def __init__(self, status_code: int, url: str) -> None:
        super().__init__(status_code, url)
        self.args = (f"explicit block from armas.es: HTTP {status_code} while requesting {url}",)


class ArmasTransportError(ArmasHttpClientError):
    """Raised when transport keeps failing after configured retries."""


class ArmasEsClient:
    """Sequential low-impact HTTP client for listing and topic pages."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        forum_id: int = DEFAULT_FORUM_ID,
        request_delay_seconds: float = 2,
        timeout_seconds: float = 20,
        max_retries: int = 3,
        user_agent: str = "PersonalForumMonitor/1.0",
        transport: Callable[..., ArmasHttpResponse] | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if request_delay_seconds < 0:
            raise ValueError("request_delay_seconds must be non-negative")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if not user_agent.strip():
            raise ValueError("user_agent must be a non-empty string")

        self.base_url = base_url.rstrip("/")
        self.forum_id = forum_id
        self.request_delay_seconds = float(request_delay_seconds)
        self.timeout_seconds = float(timeout_seconds)
        self.max_retries = max_retries
        self.user_agent = user_agent.strip()
        self._transport = transport or urllib_transport
        self._sleep = sleeper
        self._monotonic = monotonic
        self._last_request_at: float | None = None

    @classmethod
    def from_scraping_config(
        cls,
        config: ScrapingConfig,
        *,
        base_url: str = DEFAULT_BASE_URL,
        forum_id: int = DEFAULT_FORUM_ID,
        transport: Callable[..., ArmasHttpResponse] | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> ArmasEsClient:
        """Build a client from validated scraping configuration."""

        return cls(
            base_url=base_url,
            forum_id=forum_id,
            request_delay_seconds=config.request_delay_seconds,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
            user_agent=config.user_agent,
            transport=transport,
            sleeper=sleeper,
            monotonic=monotonic,
        )

    def get_listing_page(self, *, start: int = 0) -> ArmasHttpResponse:
        """GET a forum listing page without parsing it."""

        if start < 0:
            raise ValueError("start must be non-negative")
        query = {"f": str(self.forum_id)}
        if start:
            query["start"] = str(start)
        url = self._forum_url("viewforum.php", query)
        return self.get(url)

    def get_topic(self, topic_id: str | int) -> ArmasHttpResponse:
        """GET a topic page by canonical topic identity."""

        return self.get(
            canonical_topic_url(topic_id, base_url=self.base_url, forum_id=self.forum_id)
        )

    def get(self, url: str) -> ArmasHttpResponse:
        """GET a URL with bounded retries and sequential rate limiting."""

        attempts = self.max_retries + 1
        last_transport_error: Exception | None = None

        for attempt in range(attempts):
            self._respect_delay()
            try:
                response = self._transport(
                    url,
                    headers=self._headers(),
                    timeout_seconds=self.timeout_seconds,
                )
            except (TimeoutError, OSError, URLError) as exc:
                self._last_request_at = self._monotonic()
                last_transport_error = exc
                if attempt < attempts - 1:
                    continue
                raise ArmasTransportError(
                    f"transport failed after {attempts} attempts: {url}"
                ) from exc

            self._last_request_at = self._monotonic()
            if self._should_retry_response(response, url, attempt, attempts):
                continue
            return self._successful_response(response, url)

        raise ArmasTransportError(
            f"transport failed after {attempts} attempts: {url}"
        ) from last_transport_error

    def _forum_url(self, filename: str, query: Mapping[str, str]) -> str:
        base = urlsplit(self.base_url)
        path = f"/foros/{filename}"
        return urlunsplit((base.scheme, base.netloc, path, urlencode(query), ""))

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml",
        }

    def _respect_delay(self) -> None:
        if self._last_request_at is None or self.request_delay_seconds == 0:
            return
        elapsed = self._monotonic() - self._last_request_at
        remaining = self.request_delay_seconds - elapsed
        if remaining > 0:
            self._sleep(remaining)

    def _should_retry_response(
        self,
        response: ArmasHttpResponse,
        requested_url: str,
        attempt: int,
        attempts: int,
    ) -> bool:
        status_code = response.status_code
        if 200 <= status_code < 300:
            return False
        if status_code in BLOCKING_STATUS_CODES:
            raise ArmasBlockedError(status_code, requested_url)
        if status_code in TRANSIENT_STATUS_CODES and attempt < attempts - 1:
            return True
        return False

    def _successful_response(
        self,
        response: ArmasHttpResponse,
        requested_url: str,
    ) -> ArmasHttpResponse:
        status_code = response.status_code
        if 200 <= status_code < 300:
            return response
        raise ArmasHttpStatusError(status_code, requested_url)


def urllib_transport(
    url: str,
    *,
    headers: Mapping[str, str],
    timeout_seconds: float,
) -> ArmasHttpResponse:
    """Perform a single GET request with stdlib urllib."""

    request = Request(url, headers=dict(headers), method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            raw_body = response.read()
            final_url = response.geturl()
            status_code = response.status
            encoding = response.headers.get_content_charset() or "utf-8"
    except HTTPError as exc:
        raw_body = exc.read()
        final_url = exc.geturl()
        status_code = exc.code
        encoding = exc.headers.get_content_charset() or "utf-8"

    return ArmasHttpResponse(
        status_code=status_code,
        text=raw_body.decode(encoding, errors="replace"),
        final_url=final_url,
    )
