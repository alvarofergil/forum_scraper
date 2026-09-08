"""Pure parser for armas.es phpBB forum listing pages."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.models import TopicListing
from sources.armas_es.dates import ArmasDateError, parse_forum_datetime
from sources.armas_es.urls import (
    DEFAULT_BASE_URL,
    DEFAULT_FORUM_ID,
    ArmasUrlError,
    normalize_listing_page_url,
    normalize_topic_url,
)

DATE_PATTERN = re.compile(r"\d{2}\s+[A-Za-z]{3}\s+\d{4}\s+\d{2}:\d{2}")


class ParseError(ValueError):
    """Raised when a listing page cannot be parsed into trusted topic data."""


@dataclass(frozen=True, slots=True)
class ParsedListingPage:
    """Structured result extracted from a forum listing page."""

    topics: tuple[TopicListing, ...]
    next_page_url: str | None = None


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

    def child_elements(self, tag: str | None = None) -> list[_Element]:
        return [
            child
            for child in self.children
            if isinstance(child, _Element) and (tag is None or child.tag == tag)
        ]


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Element("document", {})
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = _Element(tag.lower(), {key.lower(): value or "" for key, value in attrs})
        self.stack[-1].children.append(element)
        if tag.lower() not in {"br", "hr", "img", "input", "meta", "link"}:
            self.stack.append(element)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = _Element(tag.lower(), {key.lower(): value or "" for key, value in attrs})
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


def parse_listing_page(
    html: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    forum_id: int = DEFAULT_FORUM_ID,
    current_start: int = 0,
    fallback_page_size: int = 18,
) -> ParsedListingPage:
    """Parse one armas.es listing page without performing network or storage work."""

    root = _parse_html(html)
    topic_list = _find_temas_topic_list(root)
    topics = tuple(
        _parse_topic_row(row, base_url=base_url, forum_id=forum_id)
        for row in topic_list.child_elements("li")
        if row.has_class("row") and row.first_descendant(tag="a", class_name="topictitle")
    )
    next_page_url = _find_next_page_url(
        root,
        base_url=base_url,
        forum_id=forum_id,
        current_start=current_start,
        fallback_page_size=fallback_page_size,
    )
    return ParsedListingPage(topics=topics, next_page_url=next_page_url)


def _parse_html(html: str) -> _Element:
    parser = _TreeBuilder()
    parser.feed(html)
    parser.close()
    return parser.root


def _find_temas_topic_list(root: _Element) -> _Element:
    for container in root.descendants("div"):
        classes = container.classes()
        if "forumbg" not in classes or "announcement" in classes:
            continue
        header = container.first_descendant(tag="li", class_name="header")
        if header is None or not _ascii_text(header.text()).startswith("Temas"):
            continue
        for topic_list in container.descendants("ul"):
            if {"topiclist", "topics"}.issubset(topic_list.classes()):
                return topic_list
    raise ParseError("could not find Temas topic list")


def _parse_topic_row(row: _Element, *, base_url: str, forum_id: int) -> TopicListing:
    title_link = row.first_descendant(tag="a", class_name="topictitle")
    if title_link is None:
        raise ParseError("topic row is missing title link")

    title = title_link.text()
    href = title_link.attrs.get("href", "")
    try:
        canonical_url = normalize_topic_url(href, base_url=base_url, forum_id=forum_id)
    except ArmasUrlError as exc:
        raise ParseError(f"topic row is missing topic id: {title}") from exc

    external_topic_id = dict(parse_qsl(urlsplit(canonical_url).query))["t"]
    created_author, created_at = _extract_created_metadata(row)
    last_author, last_activity_at = _extract_lastpost_metadata(row)

    return TopicListing(
        external_topic_id=external_topic_id,
        canonical_url=canonical_url,
        title=title,
        snippet=_extract_snippet(row),
        author=created_author,
        created_at=created_at,
        last_activity_at=last_activity_at,
        last_post_author=last_author,
        reply_count=_extract_count(row, "posts"),
        view_count=_extract_count(row, "views"),
    )


def _extract_snippet(row: _Element) -> str | None:
    list_inner = row.first_descendant(tag="div", class_name="list-inner")
    if list_inner is None:
        return None
    paragraph = list_inner.first_descendant(tag="p")
    if paragraph is None:
        return None
    snippet = paragraph.text()
    return snippet or None


def _extract_created_metadata(row: _Element) -> tuple[str | None, datetime | None]:
    for div in row.descendants("div"):
        if not div.has_class("responsive-hide"):
            continue
        text = div.text()
        match = re.search(r"por\s+(.+?)\s+»\s+(.+)$", text)
        if not match:
            continue
        author = match.group(1).strip()
        created_at = _parse_first_date(match.group(2))
        return author or None, created_at
    return None, None


def _extract_lastpost_metadata(row: _Element) -> tuple[str | None, datetime | None]:
    lastpost = row.first_descendant(tag="dd", class_name="lastpost")
    if lastpost is None:
        return None, None
    author_link = lastpost.first_descendant(tag="a", class_name="username")
    author = author_link.text() if author_link is not None else None
    return author, _parse_first_date(lastpost.text())


def _parse_first_date(value: str) -> datetime | None:
    match = DATE_PATTERN.search(value)
    if match is None:
        return None
    try:
        return parse_forum_datetime(match.group(0))
    except ArmasDateError as exc:
        raise ParseError(f"could not parse forum date: {match.group(0)}") from exc


def _extract_count(row: _Element, class_name: str) -> int | None:
    element = row.first_descendant(tag="dd", class_name=class_name)
    if element is None:
        return None
    match = re.search(r"\d[\d.]*", element.text())
    if match is None:
        return None
    return int(match.group(0).replace(".", ""))


def _find_next_page_url(
    root: _Element,
    *,
    base_url: str,
    forum_id: int,
    current_start: int,
    fallback_page_size: int,
) -> str | None:
    for item in root.descendants("li"):
        if not item.has_class("next"):
            continue
        link = item.first_descendant(tag="a")
        if link is not None and link.attrs.get("rel") == "next":
            return _clean_forum_url(
                link.attrs.get("href", ""),
                base_url=base_url,
                forum_id=forum_id,
            )

    metadata_url = _next_page_from_metadata(
        root,
        base_url=base_url,
        forum_id=forum_id,
        current_start=current_start,
    )
    if metadata_url is not None:
        return metadata_url

    if fallback_page_size <= 0:
        return None
    return _build_forum_page_url(
        f"viewforum.php?f={forum_id}",
        base_url=base_url,
        forum_id=forum_id,
        start=current_start + fallback_page_size,
        start_name="start",
    )


def _next_page_from_metadata(
    root: _Element,
    *,
    base_url: str,
    forum_id: int,
    current_start: int,
) -> str | None:
    for input_element in root.descendants("input"):
        per_page = input_element.attrs.get("data-per-page")
        start_name = input_element.attrs.get("data-start-name", "start")
        page_base_url = input_element.attrs.get("data-base-url")
        if not per_page or not page_base_url:
            continue
        if start_name != "start":
            continue
        try:
            next_start = current_start + int(per_page)
        except ValueError:
            continue
        return _build_forum_page_url(
            page_base_url,
            base_url=base_url,
            forum_id=forum_id,
            start=next_start,
            start_name=start_name,
        )
    return None


def _build_forum_page_url(
    url: str,
    *,
    base_url: str,
    forum_id: int,
    start: int,
    start_name: str,
) -> str | None:
    resolved_url = _clean_forum_url(unescape(url), base_url=base_url, forum_id=forum_id)
    if resolved_url is None:
        return None
    parts = urlsplit(resolved_url)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key != start_name
    ]
    query.append((start_name, str(start)))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def _clean_forum_url(url: str, *, base_url: str, forum_id: int) -> str | None:
    try:
        return normalize_listing_page_url(url, base_url=base_url, forum_id=forum_id)
    except ArmasUrlError:
        return None


def _ascii_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(character for character in normalized if not unicodedata.combining(character))
