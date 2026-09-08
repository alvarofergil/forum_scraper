"""Pure parser for armas.es phpBB topic pages."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlsplit

from app.models import ParsedTopic, TopicPost
from sources.armas_es.dates import ArmasDateError, parse_forum_datetime
from sources.armas_es.urls import (
    DEFAULT_BASE_URL,
    DEFAULT_FORUM_ID,
    ArmasUrlError,
    normalize_topic_url,
)

DATE_PATTERN = re.compile(r"\d{2}\s+[A-Za-z]{3}\s+\d{4}\s+\d{2}:\d{2}")


class ParseError(ValueError):
    """Raised when a topic page cannot be parsed into trusted post data."""


@dataclass(slots=True)
class _Element:
    tag: str
    attrs: dict[str, str]
    children: list[_Element | str] = field(default_factory=list)

    def text(self) -> str:
        chunks: list[str] = []
        for child in self.children:
            if isinstance(child, str):
                chunks.append(child)
            else:
                chunks.append(child.text())
        return " ".join("".join(chunks).split())

    def classes(self) -> set[str]:
        return set(self.attrs.get("class", "").split())

    def has_class(self, class_name: str) -> bool:
        return class_name in self.classes()

    def descendants(self, tag: str | None = None) -> list[_Element]:
        found: list[_Element] = []
        for child in self.children:
            if isinstance(child, _Element):
                if tag is None or child.tag == tag:
                    found.append(child)
                found.extend(child.descendants(tag))
        return found

    def first_descendant(
        self,
        *,
        tag: str | None = None,
        class_name: str | None = None,
    ) -> _Element | None:
        for node in self.descendants(tag):
            if class_name is None or node.has_class(class_name):
                return node
        return None


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Element("document", {})
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attributes = {key.lower(): value or "" for key, value in attrs}
        if tag == "br":
            self.stack[-1].children.append("\n")
            return
        if tag == "img":
            if attributes.get("alt"):
                self.stack[-1].children.append(f" {attributes['alt']} ")
            return

        element = _Element(tag, attributes)
        self.stack[-1].children.append(element)
        if tag not in {"hr", "img", "input", "meta", "link"}:
            self.stack.append(element)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attributes = {key.lower(): value or "" for key, value in attrs}
        if tag == "br":
            self.stack[-1].children.append("\n")
            return
        if tag == "img":
            if attributes.get("alt"):
                self.stack[-1].children.append(f" {attributes['alt']} ")
            return
        element = _Element(tag, attributes)
        self.stack[-1].children.append(element)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.stack[-1].children.append(data)


def parse_topic_page(
    html: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    forum_id: int = DEFAULT_FORUM_ID,
) -> ParsedTopic:
    """Parse one armas.es topic page without fetching additional pages."""

    root = _parse_html(html)
    title, external_topic_id = _extract_title_and_topic_id(
        root,
        base_url=base_url,
        forum_id=forum_id,
    )
    posts = tuple(_parse_post(post, index) for index, post in enumerate(_post_nodes(root), start=1))
    if not posts:
        raise ParseError("topic page does not contain visible posts")

    current_page, total_pages = _extract_pagination(root)
    return ParsedTopic(
        topic_title=title,
        external_topic_id=external_topic_id,
        original_author=posts[0].author,
        total_posts=_extract_total_posts(root),
        current_page=current_page,
        total_pages=total_pages,
        posts=posts,
    )


def _parse_html(html: str) -> _Element:
    parser = _TreeBuilder()
    parser.feed(html)
    parser.close()
    return parser.root


def _extract_title_and_topic_id(
    root: _Element,
    *,
    base_url: str,
    forum_id: int,
) -> tuple[str, str]:
    title_heading = root.first_descendant(tag="h2", class_name="topic-title")
    title_link = title_heading.first_descendant(tag="a") if title_heading is not None else None
    if title_link is None:
        raise ParseError("topic page is missing topic title")

    try:
        canonical_url = normalize_topic_url(
            title_link.attrs.get("href", ""),
            base_url=base_url,
            forum_id=forum_id,
        )
    except ArmasUrlError as exc:
        raise ParseError("topic page is missing topic id") from exc

    external_topic_id = dict(parse_qsl(urlsplit(canonical_url).query))["t"]
    return title_link.text(), external_topic_id


def _post_nodes(root: _Element) -> list[_Element]:
    return [
        node
        for node in root.descendants("div")
        if node.has_class("post") and re.fullmatch(r"p\d+", node.attrs.get("id", ""))
    ]


def _parse_post(post: _Element, sequence_number: int) -> TopicPost:
    author_line = post.first_descendant(tag="p", class_name="author")
    content = post.first_descendant(tag="div", class_name="content")
    if author_line is None or content is None:
        raise ParseError("topic post is missing author metadata or content")

    author = _extract_author(author_line)
    posted_at = _extract_posted_at(author_line)
    text = content.text()
    if not text:
        raise ParseError("topic post is missing clean text")

    return TopicPost(
        sequence_number=sequence_number,
        external_post_id=post.attrs["id"].removeprefix("p"),
        author=author,
        posted_at=posted_at,
        text=text,
    )


def _extract_author(author_line: _Element) -> str:
    strong = author_line.first_descendant(tag="strong")
    if strong is not None:
        author = strong.text()
        if author:
            return author

    text = author_line.text()
    match = re.search(r"por\s+(.+?)\s+»", text)
    if match:
        return match.group(1).strip()
    raise ParseError("topic post is missing author")


def _extract_posted_at(author_line: _Element) -> datetime:
    match = DATE_PATTERN.search(author_line.text())
    if match is None:
        raise ParseError("topic post is missing posted date")
    try:
        return parse_forum_datetime(match.group(0))
    except ArmasDateError as exc:
        raise ParseError(f"could not parse forum date: {match.group(0)}") from exc


def _extract_total_posts(root: _Element) -> int | None:
    pagination = root.first_descendant(tag="div", class_name="pagination")
    if pagination is None:
        return None
    match = re.search(r"(\d[\d.]*)\s+mensajes?", pagination.text())
    if match is None:
        return None
    return int(match.group(1).replace(".", ""))


def _extract_pagination(root: _Element) -> tuple[int, int]:
    pagination = root.first_descendant(tag="div", class_name="pagination")
    if pagination is None:
        return 1, 1

    text = _ascii_text(pagination.text())
    match = re.search(r"Pagina\s+(\d+)\s+de\s+(\d+)", text)
    if match:
        return int(match.group(1)), int(match.group(2))

    page_numbers: list[int] = []
    current_page = 1
    for item in pagination.descendants("li"):
        item_text = item.text()
        if item_text.isdigit():
            page_number = int(item_text)
            page_numbers.append(page_number)
            if item.has_class("active"):
                current_page = page_number

    if not page_numbers:
        return current_page, current_page
    return current_page, max(page_numbers)


def _ascii_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(character for character in normalized if not unicodedata.combining(character))
