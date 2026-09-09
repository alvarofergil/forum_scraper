from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.models import ParsedTopic, TopicPost
from sources.armas_es.client import (
    ArmasHttpResponse,
    ArmasHttpTransientError,
)
from sources.armas_es.topic_fetcher import ArmasEsTopicFetcher
from sources.base import TopicFetchParseError, TopicFetchTransientError

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "armas_es"


def read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


class FakeClient:
    def __init__(self, responses: Mapping[str, str]) -> None:
        self.responses = dict(responses)
        self.calls: list[str] = []

    def get(self, url: str) -> ArmasHttpResponse:
        self.calls.append(url)
        html = self.responses[url]
        return ArmasHttpResponse(status_code=200, text=html, final_url=url)


def test_fetch_topic_combines_multipage_posts_sequentially() -> None:
    first_url = "https://www.armas.es/foros/viewtopic.php?f=96&t=1181036"
    second_url = "https://www.armas.es/foros/viewtopic.php?f=96&t=1181036&start=18"
    client = FakeClient(
        {
            first_url: read_fixture("topic_multipage_page_1.html"),
            second_url: read_fixture("topic_multipage_page_2.html"),
        }
    )
    fetcher = ArmasEsTopicFetcher(client=client)

    topic = fetcher.fetch_topic(
        external_topic_id="1181036",
        canonical_url=first_url,
    )

    assert client.calls == [first_url, second_url]
    assert topic.external_topic_id == "1181036"
    assert topic.current_page == 1
    assert topic.total_pages == 2
    assert len(topic.posts) == 20
    assert topic.posts[0].sequence_number == 1
    assert topic.posts[-1].sequence_number == 20
    assert topic.posts[-1].external_post_id == "4471083"


def test_fetch_topic_deduplicates_posts_by_external_post_id() -> None:
    first_url = "https://www.armas.es/foros/viewtopic.php?f=96&t=1181036"
    second_url = "https://www.armas.es/foros/viewtopic.php?f=96&t=1181036&start=18"
    duplicate_page = read_fixture("topic_multipage_page_2.html").replace("4471083", "4469107")
    client = FakeClient(
        {
            first_url: read_fixture("topic_multipage_page_1.html"),
            second_url: duplicate_page,
        }
    )
    fetcher = ArmasEsTopicFetcher(client=client)

    topic = fetcher.fetch_topic(
        external_topic_id="1181036",
        canonical_url=first_url,
    )

    assert len(topic.posts) == 19
    assert [post.external_post_id for post in topic.posts].count("4469107") == 1
    assert [post.sequence_number for post in topic.posts] == list(range(1, 20))


def test_fetch_topic_transient_error_on_later_page_does_not_return_partial_topic() -> None:
    first_url = "https://www.armas.es/foros/viewtopic.php?f=96&t=1181036"
    second_url = "https://www.armas.es/foros/viewtopic.php?f=96&t=1181036&start=18"

    class FailingSecondPageClient(FakeClient):
        def get(self, url: str) -> ArmasHttpResponse:
            self.calls.append(url)
            if url == second_url:
                raise ArmasHttpTransientError(503, second_url)
            html = self.responses[url]
            return ArmasHttpResponse(status_code=200, text=html, final_url=url)

    client = FailingSecondPageClient({first_url: read_fixture("topic_multipage_page_1.html")})
    fetcher = ArmasEsTopicFetcher(client=client)

    with pytest.raises(TopicFetchTransientError):
        fetcher.fetch_topic(external_topic_id="1181036", canonical_url=first_url)

    assert client.calls == [first_url, second_url]


def test_fetch_topic_rejects_inconsistent_pagination() -> None:
    first_url = "https://www.armas.es/foros/viewtopic.php?f=96&t=1181036"
    fetcher = ArmasEsTopicFetcher(
        client=FakeClient({first_url: "<unused>"}),
        parser=lambda _html, **_kwargs: read_invalid_topic(),
    )

    with pytest.raises(TopicFetchParseError, match="pagination"):
        fetcher.fetch_topic(external_topic_id="1181036", canonical_url=first_url)


def test_topic_fetcher_passes_custom_base_url_and_forum_id_to_parser() -> None:
    first_url = "https://example.test/foros/viewtopic.php?f=123&t=555"
    captured: dict[str, object] = {}

    def parser(html: str, *, base_url: str, forum_id: int) -> ParsedTopic:
        captured["html"] = html
        captured["base_url"] = base_url
        captured["forum_id"] = forum_id
        return ParsedTopic(
            topic_title="Vendo Acme Target Pro",
            external_topic_id="555",
            original_author="seller",
            total_posts=1,
            current_page=1,
            total_pages=1,
            posts=(
                TopicPost(
                    sequence_number=1,
                    author="seller",
                    posted_at=datetime(2026, 1, 2, 10, 30, tzinfo=UTC),
                    text="Acme Target Pro",
                    external_post_id="p1",
                ),
            ),
        )

    client = FakeClient({first_url: "<html>topic</html>"})
    fetcher = ArmasEsTopicFetcher(
        client=client,
        parser=parser,
        base_url="https://example.test",
        forum_id=123,
    )

    topic = fetcher.fetch_topic(external_topic_id="555", canonical_url=first_url)

    assert topic.external_topic_id == "555"
    assert captured == {
        "html": "<html>topic</html>",
        "base_url": "https://example.test",
        "forum_id": 123,
    }


def read_invalid_topic():  # type: ignore[no-untyped-def]
    from app.models import ParsedTopic

    topic = ArmasEsTopicFetcher.__name__
    assert topic
    return ParsedTopic(
        topic_title="Broken",
        external_topic_id="1181036",
        original_author="seller",
        total_posts=1,
        current_page=2,
        total_pages=1,
        posts=(),
    )
