from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from sources.armas_es.listing_parser import ParseError, parse_listing_page

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "armas_es"


def read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_parse_listing_extracts_only_ordinary_topics_from_temas_block() -> None:
    page = parse_listing_page(read_fixture("listing_page_1.html"))

    topic_ids = [topic.external_topic_id for topic in page.topics]

    assert len(page.topics) == 18
    assert topic_ids[:3] == ["1182533", "1182532", "1182457"]
    assert "882510" not in topic_ids
    assert "904287" not in topic_ids


def test_parse_listing_extracts_metadata_and_canonical_urls() -> None:
    page = parse_listing_page(read_fixture("listing_page_1.html"))
    topic = page.topics[5]

    assert topic.external_topic_id == "1181036"
    assert topic.canonical_url == "https://www.armas.es/foros/viewtopic.php?f=96&t=1181036"
    assert topic.title == "Busco CZ Shadow 2 [OR]"
    assert topic.snippet is not None
    assert "CZ Shadow 2" in topic.snippet
    assert topic.author == "user_009"
    assert topic.created_at == datetime(2026, 7, 10, 14, 47, tzinfo=UTC)
    assert topic.last_activity_at == datetime(2026, 9, 7, 14, 18, tzinfo=UTC)
    assert topic.last_post_author == "user_009"
    assert topic.reply_count == 19
    assert topic.view_count == 1457
    assert topic.next_page_url is None


def test_parse_listing_detects_next_page_and_removes_session_ids() -> None:
    page = parse_listing_page(read_fixture("listing_page_2.html"))

    assert page.next_page_url == "https://www.armas.es/foros/viewforum.php?f=96&start=36"
    assert "sid" not in page.next_page_url


def test_parse_listing_uses_page_metadata_fallback_for_next_page() -> None:
    html = """
    <div id="page-body">
      <div class="pagination">
        <input data-per-page="18" data-base-url="./viewforum.php?f=96" data-start-name="start" />
      </div>
      <div class="forumbg">
        <ul class="topiclist"><li class="header"><dl><dt><div>Temas</div></dt></dl></li></ul>
        <ul class="topiclist topics"></ul>
      </div>
    </div>
    """

    page = parse_listing_page(html, current_start=18)

    assert page.next_page_url == "https://www.armas.es/foros/viewforum.php?f=96&start=36"


def test_parse_listing_uses_configurable_start_step_fallback() -> None:
    html = """
    <div id="page-body">
      <div class="forumbg">
        <ul class="topiclist"><li class="header"><dl><dt><div>Temas</div></dt></dl></li></ul>
        <ul class="topiclist topics"></ul>
      </div>
    </div>
    """

    page = parse_listing_page(html, current_start=36, fallback_page_size=18)

    assert page.next_page_url == "https://www.armas.es/foros/viewforum.php?f=96&start=54"


def test_parse_listing_raises_parse_error_without_temas_block() -> None:
    html = '<div id="page-body"><div class="forumbg announcement">Anuncios</div></div>'

    with pytest.raises(ParseError, match="Temas"):
        parse_listing_page(html)


def test_parse_listing_raises_parse_error_for_topic_without_identity() -> None:
    html = """
    <div id="page-body">
      <div class="forumbg">
        <ul class="topiclist"><li class="header"><dl><dt><div>Temas</div></dt></dl></li></ul>
        <ul class="topiclist topics">
          <li class="row"><a class="topictitle" href="./viewtopic.php?f=96">Broken</a></li>
        </ul>
      </div>
    </div>
    """

    with pytest.raises(ParseError, match="topic id"):
        parse_listing_page(html)
