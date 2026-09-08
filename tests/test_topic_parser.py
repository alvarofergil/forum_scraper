from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from sources.armas_es.topic_parser import ParseError, parse_topic_page

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "armas_es"


def read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_parse_one_page_topic_extracts_title_author_pagination_and_post() -> None:
    topic = parse_topic_page(read_fixture("topic_legal_notice.html"))

    assert topic.external_topic_id == "882510"
    assert topic.topic_title == "AVISO LEGAL COMPRA-VENTA ENTRE PARTICULARES"
    assert topic.original_author == "armas.es"
    assert topic.total_posts == 1
    assert topic.current_page == 1
    assert topic.total_pages == 1
    assert len(topic.posts) == 1

    post = topic.posts[0]
    assert post.external_post_id == "994889"
    assert post.sequence_number == 1
    assert post.author == "armas.es"
    assert post.posted_at == datetime(2009, 12, 16, 14, 52, tzinfo=UTC)
    assert "Armas.es no participa" in post.text
    assert "Herramientas de Tema" not in post.text
    assert "Reporte este mensaje" not in post.text


def test_parse_multipage_topic_first_page_extracts_visible_posts_only() -> None:
    topic = parse_topic_page(read_fixture("topic_multipage_page_1.html"))

    assert topic.external_topic_id == "1181036"
    assert topic.topic_title == "Busco CZ Shadow 2 [OR]"
    assert topic.original_author == "user_009"
    assert topic.total_posts == 20
    assert topic.current_page == 1
    assert topic.total_pages == 2
    assert len(topic.posts) == 18
    assert topic.posts[0].external_post_id == "4461618"
    assert topic.posts[0].posted_at == datetime(2026, 7, 10, 14, 47, tzinfo=UTC)
    assert "Interesado en adquirir CZ Shadow 2" in topic.posts[0].text
    assert topic.posts[-1].external_post_id == "4467558"


def test_parse_multipage_topic_second_page_detects_current_page() -> None:
    topic = parse_topic_page(read_fixture("topic_multipage_page_2.html"))

    assert topic.external_topic_id == "1181036"
    assert topic.current_page == 2
    assert topic.total_pages == 2
    assert topic.total_posts == 20
    assert len(topic.posts) == 2
    assert [post.external_post_id for post in topic.posts] == ["4469107", "4471083"]


def test_parse_topic_preserves_clean_text_not_html() -> None:
    topic = parse_topic_page(read_fixture("topic_multipage_page_1.html"))

    assert "<br" not in topic.posts[0].text
    assert "<img" not in topic.posts[0].text
    assert "1300" in topic.posts[0].text


def test_parse_topic_raises_parse_error_without_topic_identity() -> None:
    html = """
    <div id="page-body">
      <h2 class="topic-title"><a href="./viewtopic.php?f=96">Broken</a></h2>
      <div id="p1" class="post">
        <div class="postbody">
          <p class="author">por <strong>user_001</strong> &raquo; 01 Ene 2026 10:00</p>
          <div class="content">Body</div>
        </div>
      </div>
    </div>
    """

    with pytest.raises(ParseError, match="topic id"):
        parse_topic_page(html)


def test_parse_topic_raises_parse_error_without_posts() -> None:
    html = """
    <div id="page-body">
      <h2 class="topic-title"><a href="./viewtopic.php?f=96&amp;t=123">Broken</a></h2>
    </div>
    """

    with pytest.raises(ParseError, match="posts"):
        parse_topic_page(html)
