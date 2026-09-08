"""Source-neutral contracts for fetching parsed forum content."""

from __future__ import annotations

from typing import Protocol

from app.models import ParsedTopic


class TopicFetchError(RuntimeError):
    """Base error raised while fetching a complete topic from any source."""


class TopicFetchRecoverableError(TopicFetchError):
    """Raised when a check should be retried later without changing availability."""


class TopicFetchTransientError(TopicFetchRecoverableError):
    """Raised for transport, HTTP or site states that may recover later."""


class TopicFetchParseError(TopicFetchRecoverableError):
    """Raised when fetched topic pages are incomplete or inconsistent."""


class TopicFetchNotFoundError(TopicFetchError):
    """Raised when a source confirms that a topic does not exist."""


class TopicFetchUnavailableError(TopicFetchError):
    """Raised when a source confirms that a topic is no longer available."""


class TopicFetcher(Protocol):
    """Fetch a complete parsed topic without exposing source-specific details."""

    def fetch_topic(
        self,
        *,
        external_topic_id: str,
        canonical_url: str | None = None,
    ) -> ParsedTopic:
        """Return a complete parsed topic for favorite monitoring."""
