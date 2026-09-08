"""Fetch complete armas.es topics by combining phpBB pages sequentially."""

from __future__ import annotations

from collections.abc import Callable

from app.models import ParsedTopic, TopicPost
from sources.armas_es.client import (
    ArmasEsClient,
    ArmasHttpClientError,
    ArmasTopicNotFoundError,
    ArmasTopicUnavailableError,
)
from sources.armas_es.topic_parser import ParseError, parse_topic_page
from sources.armas_es.urls import (
    DEFAULT_BASE_URL,
    DEFAULT_FORUM_ID,
    ArmasUrlError,
    canonical_topic_page_url,
    canonical_topic_url,
    normalize_topic_url,
)
from sources.base import (
    TopicFetchNotFoundError,
    TopicFetchParseError,
    TopicFetchTransientError,
    TopicFetchUnavailableError,
)

TopicParser = Callable[[str], ParsedTopic]


class ArmasEsTopicFetcher:
    """Fetch and parse complete armas.es topics behind a source-neutral contract."""

    def __init__(
        self,
        *,
        client: ArmasEsClient,
        parser: TopicParser = parse_topic_page,
        base_url: str = DEFAULT_BASE_URL,
        forum_id: int = DEFAULT_FORUM_ID,
    ) -> None:
        self.client = client
        self.parser = parser
        self.base_url = base_url
        self.forum_id = forum_id

    def fetch_topic(
        self,
        *,
        external_topic_id: str,
        canonical_url: str | None = None,
    ) -> ParsedTopic:
        """Return one parsed topic including all advertised pages."""

        first_url = self._first_page_url(external_topic_id, canonical_url)
        first = self._fetch_and_parse(first_url)
        self._validate_page(first, expected_topic_id=external_topic_id, expected_page=1)

        page_size = len(first.posts)
        pages = [first]
        for page_number in range(2, first.total_pages + 1):
            if page_size <= 0:
                raise TopicFetchParseError("topic pagination cannot be followed without posts")
            page_url = canonical_topic_page_url(
                external_topic_id,
                start=(page_number - 1) * page_size,
                base_url=self.base_url,
                forum_id=self.forum_id,
            )
            page = self._fetch_and_parse(page_url)
            self._validate_page(
                page,
                expected_topic_id=external_topic_id,
                expected_page=page_number,
                expected_total_pages=first.total_pages,
            )
            pages.append(page)

        return self._combine_pages(pages)

    def _first_page_url(self, external_topic_id: str, canonical_url: str | None) -> str:
        if canonical_url is None:
            return canonical_topic_url(
                external_topic_id,
                base_url=self.base_url,
                forum_id=self.forum_id,
            )
        try:
            return normalize_topic_url(
                canonical_url,
                base_url=self.base_url,
                forum_id=self.forum_id,
            )
        except ArmasUrlError as exc:
            raise TopicFetchParseError("topic canonical URL is invalid") from exc

    def _fetch_and_parse(self, url: str) -> ParsedTopic:
        try:
            response = self.client.get(url)
            return self.parser(response.text)
        except ArmasTopicNotFoundError as exc:
            raise TopicFetchNotFoundError("topic not found") from exc
        except ArmasTopicUnavailableError as exc:
            raise TopicFetchUnavailableError("topic unavailable") from exc
        except ArmasHttpClientError as exc:
            raise TopicFetchTransientError("topic fetch failed transiently") from exc
        except ParseError as exc:
            raise TopicFetchParseError("topic page could not be parsed") from exc

    def _validate_page(
        self,
        page: ParsedTopic,
        *,
        expected_topic_id: str,
        expected_page: int,
        expected_total_pages: int | None = None,
    ) -> None:
        if page.external_topic_id != expected_topic_id:
            raise TopicFetchParseError("topic page identity does not match requested topic")
        if page.current_page != expected_page:
            raise TopicFetchParseError("topic pagination current page is inconsistent")
        if page.total_pages < page.current_page or page.total_pages < 1:
            raise TopicFetchParseError("topic pagination is inconsistent")
        if expected_total_pages is not None and page.total_pages != expected_total_pages:
            raise TopicFetchParseError("topic pagination total pages changed during fetch")

    def _combine_pages(self, pages: list[ParsedTopic]) -> ParsedTopic:
        first = pages[0]
        posts = self._deduplicate_posts(pages)
        return ParsedTopic(
            topic_title=first.topic_title,
            external_topic_id=first.external_topic_id,
            original_author=first.original_author,
            total_posts=first.total_posts,
            current_page=1,
            total_pages=first.total_pages,
            posts=posts,
        )

    def _deduplicate_posts(self, pages: list[ParsedTopic]) -> tuple[TopicPost, ...]:
        seen: set[str] = set()
        output: list[TopicPost] = []
        for page in pages:
            for post in page.posts:
                dedupe_key = (
                    post.external_post_id
                    or f"page:{page.current_page}:seq:{post.sequence_number}"
                )
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                output.append(
                    TopicPost(
                        sequence_number=len(output) + 1,
                        author=post.author,
                        posted_at=post.posted_at,
                        text=post.text,
                        external_post_id=post.external_post_id,
                    )
                )
        return tuple(output)
