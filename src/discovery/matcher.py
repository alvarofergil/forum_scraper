"""Deterministic watchlist matching for forum listing metadata."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.models import TopicListing, WatchItem

PUNCTUATION_PATTERN = re.compile(r"[^\w\s]", flags=re.UNICODE)
WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class WatchlistMatch:
    """A cheap deterministic candidate match for one configured watch item."""

    watch_item: WatchItem
    reason: str
    matched_text: str


def normalize_text(value: str) -> str:
    """Normalize text for cheap deterministic matching."""

    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    lowered = without_marks.lower()
    without_punctuation = PUNCTUATION_PATTERN.sub(" ", lowered)
    return WHITESPACE_PATTERN.sub(" ", without_punctuation).strip()


def match_listing(
    listing: TopicListing,
    watchlist: tuple[WatchItem, ...],
) -> tuple[WatchlistMatch, ...]:
    """Return watchlist candidates found in a listing title and snippet."""

    return match_text(listing.title, listing.snippet, watchlist)


def match_text(
    title: str,
    snippet: str | None,
    watchlist: tuple[WatchItem, ...],
) -> tuple[WatchlistMatch, ...]:
    """Return watchlist candidates found in plain listing text."""

    haystack = normalize_text(" ".join(part for part in (title, snippet) if part))
    matches: list[WatchlistMatch] = []
    for watch_item in watchlist:
        alias_match = _matching_alias(haystack, watch_item.aliases)
        if alias_match is not None:
            matches.append(
                WatchlistMatch(
                    watch_item=watch_item,
                    reason="alias",
                    matched_text=alias_match,
                )
            )
            continue

        if _contains_phrase(haystack, watch_item.brand) and _contains_phrase(
            haystack,
            watch_item.model,
        ):
            matches.append(
                WatchlistMatch(
                    watch_item=watch_item,
                    reason="brand_model",
                    matched_text=f"{watch_item.brand} {watch_item.model}",
                )
            )

    return tuple(matches)


def _matching_alias(haystack: str, aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        if _contains_phrase(haystack, alias):
            return alias
    return None


def _contains_phrase(haystack: str, phrase: str) -> bool:
    normalized_phrase = normalize_text(phrase)
    if not normalized_phrase:
        return False
    return normalized_phrase in haystack or _compact(normalized_phrase) in _compact(haystack)


def _compact(value: str) -> str:
    return value.replace(" ", "")
