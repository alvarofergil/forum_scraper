from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models import AvailabilityStatus, ListingType, ParsedTopic, TopicPost, WatchItem
from classification.base import ClassificationContext, ClassificationResult, PreviousFavoriteState
from classification.fake import FakeClassifier


def parsed_topic() -> ParsedTopic:
    return ParsedTopic(
        topic_title="Vendo Acme Target Pro",
        external_topic_id="123",
        original_author="seller_001",
        total_posts=1,
        current_page=1,
        total_pages=1,
        posts=(
            TopicPost(
                sequence_number=1,
                author="seller_001",
                posted_at=datetime(2026, 1, 2, 10, 30, tzinfo=UTC),
                text="Acme Target Pro en buen estado por 123 EUR",
                external_post_id="456",
            ),
        ),
    )


def watch_item() -> WatchItem:
    return WatchItem(id="item_001", brand="Acme", model="Target Pro")


def test_classification_result_is_structured_and_can_represent_non_match() -> None:
    result = ClassificationResult(
        matches_watch_item=False,
        listing_type=ListingType.DISCUSSION,
        availability=AvailabilityStatus.UNKNOWN,
        price=None,
        currency=None,
        confidence=0.12,
        evidence=("mentions model in a discussion",),
    )

    assert result.matches_watch_item is False
    assert result.price is None
    assert result.model_dump(mode="json")["listing_type"] == "DISCUSSION"


def test_classification_result_rejects_invalid_availability() -> None:
    with pytest.raises(ValidationError):
        ClassificationResult(
            matches_watch_item=True,
            listing_type=ListingType.OFFER,
            availability="available",
            price=123,
            currency="EUR",
            confidence=0.9,
        )


def test_classification_result_rejects_invalid_listing_type() -> None:
    with pytest.raises(ValidationError):
        ClassificationResult(
            matches_watch_item=True,
            listing_type="INVALID",
            availability=AvailabilityStatus.AVAILABLE,
            confidence=0.9,
        )


def test_classification_result_requires_match_decision() -> None:
    with pytest.raises(ValidationError):
        ClassificationResult(
            listing_type=ListingType.OFFER,
            availability=AvailabilityStatus.AVAILABLE,
            confidence=0.9,
        )


def test_classification_result_rejects_confidence_outside_range() -> None:
    with pytest.raises(ValidationError):
        ClassificationResult(
            matches_watch_item=True,
            listing_type=ListingType.OFFER,
            availability=AvailabilityStatus.AVAILABLE,
            confidence=1.01,
        )


def test_classification_result_rejects_negative_price() -> None:
    with pytest.raises(ValidationError):
        ClassificationResult(
            matches_watch_item=True,
            listing_type=ListingType.OFFER,
            availability=AvailabilityStatus.AVAILABLE,
            price=-1,
            currency="EUR",
            confidence=0.9,
        )


def test_fake_classifier_returns_configured_candidate_responses() -> None:
    expected = ClassificationResult(
        matches_watch_item=True,
        listing_type=ListingType.OFFER,
        availability=AvailabilityStatus.AVAILABLE,
        price=123.45,
        currency="EUR",
        confidence=0.93,
        evidence=("title and first post match",),
    )
    classifier = FakeClassifier(new_candidate_results={("item_001", "123"): expected})

    result = classifier.classify_new_candidate(watch_item(), parsed_topic())

    assert result == expected
    assert classifier.new_candidate_calls == ((watch_item(), parsed_topic()),)


def test_fake_classifier_returns_configured_favorite_update_responses() -> None:
    expected = ClassificationResult(
        matches_watch_item=True,
        listing_type=ListingType.OFFER,
        availability=AvailabilityStatus.RESERVED,
        price=None,
        currency=None,
        confidence=0.88,
    )
    previous = PreviousFavoriteState(
        availability=AvailabilityStatus.AVAILABLE,
        price=123.45,
        currency="EUR",
        content_hash="old-hash",
    )
    classifier = FakeClassifier(favorite_update_results={("item_001", "123"): expected})

    result = classifier.classify_favorite_update(previous, watch_item(), parsed_topic())

    assert result == expected
    assert classifier.favorite_update_calls == ((previous, watch_item(), parsed_topic()),)


def test_fake_classifier_default_response_keeps_candidates_pending_safely() -> None:
    classifier = FakeClassifier()

    result = classifier.classify_new_candidate(watch_item(), parsed_topic())

    assert result.matches_watch_item is False
    assert result.listing_type == ListingType.OTHER
    assert result.availability == AvailabilityStatus.UNKNOWN
    assert result.price is None


def test_fake_classifier_can_raise_configured_errors() -> None:
    classifier = FakeClassifier(error=RuntimeError("classifier unavailable"))

    with pytest.raises(RuntimeError, match="classifier unavailable"):
        classifier.classify_new_candidate(watch_item(), parsed_topic())


def test_classification_context_carries_clean_structured_input_only() -> None:
    context = ClassificationContext.from_topic(watch_item(), parsed_topic())

    assert context.watch_item_id == "item_001"
    assert context.topic_title == "Vendo Acme Target Pro"
    assert context.original_author == "seller_001"
    assert context.posts[0].text == "Acme Target Pro en buen estado por 123 EUR"
    assert context.posts[0].posted_at == "2026-01-02T10:30:00Z"
    assert "<html" not in context.model_dump_json().lower()
