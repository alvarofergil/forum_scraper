from __future__ import annotations

from app.models import TopicListing, WatchItem
from discovery.matcher import match_listing, match_text, normalize_text


def listing(title: str, snippet: str | None = None) -> TopicListing:
    return TopicListing(
        external_topic_id="123",
        canonical_url="https://www.armas.es/foros/viewtopic.php?f=96&t=123",
        title=title,
        snippet=snippet,
    )


def test_normalize_text_covers_unicode_case_hyphens_punctuation_and_spaces() -> None:
    assert normalize_text("  PÍSTOLA -- Réplica,  modelo-X  ") == "pistola replica modelo x"


def test_brand_and_model_detect_candidate_from_title_and_snippet() -> None:
    watch_item = WatchItem(id="item_001", brand="Acme", model="Target Pro")
    topic = listing("Se vende ACME", "Target-Pro con maletin")

    matches = match_listing(topic, (watch_item,))

    assert len(matches) == 1
    assert matches[0].watch_item == watch_item
    assert matches[0].reason == "brand_model"


def test_only_brand_does_not_match_by_default() -> None:
    watch_item = WatchItem(id="item_001", brand="Acme", model="Target Pro")
    topic = listing("Vendo Acme impecable", "sin mas detalles")

    assert match_listing(topic, (watch_item,)) == ()


def test_only_model_does_not_match_by_default() -> None:
    watch_item = WatchItem(id="item_001", brand="Acme", model="Target Pro")
    topic = listing("Target Pro en venta")

    assert match_listing(topic, (watch_item,)) == ()


def test_alias_detects_candidate_without_brand_and_model_pair() -> None:
    watch_item = WatchItem(
        id="item_001",
        brand="Acme",
        model="Target Pro",
        aliases=("TPRO competition",),
    )

    matches = match_text("Vendo T-Pro Competition", None, (watch_item,))

    assert len(matches) == 1
    assert matches[0].reason == "alias"
    assert matches[0].matched_text == "TPRO competition"


def test_multiple_watch_items_can_match_same_listing() -> None:
    watch_items = (
        WatchItem(id="item_001", brand="Acme", model="Target Pro"),
        WatchItem(id="item_002", brand="Example", model="Compact"),
    )

    matches = match_text("Acme Target Pro con cambio por Example Compact", None, watch_items)

    assert [match.watch_item.id for match in matches] == ["item_001", "item_002"]
