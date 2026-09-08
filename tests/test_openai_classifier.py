from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.config import AiConfig, ConfigError
from app.models import AvailabilityStatus, ListingType, ParsedTopic, TopicPost, WatchItem
from classification.base import PreviousFavoriteState
from classification.openai_classifier import OpenAIClassifier


class FakeResponses:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return self


class FakeOpenAIClient:
    def __init__(self, output_text: str) -> None:
        self.responses = FakeResponses(output_text)


def topic_with_html_markers() -> ParsedTopic:
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
                text="Acme Target Pro por 123 EUR. <html tag mentioned as plain text>",
                external_post_id="456",
            ),
        ),
    )


def watch_item() -> WatchItem:
    return WatchItem(id="item_001", brand="Acme", model="Target Pro", aliases=("Target-Pro",))


def valid_output() -> str:
    return """
    {
      "matches_watch_item": true,
      "listing_type": "OFFER",
      "availability": "AVAILABLE",
      "price": 123.45,
      "currency": "EUR",
      "confidence": 0.93,
      "evidence": ["brand and model appear in first post"]
    }
    """


def test_from_config_rejects_enabled_ai_without_model() -> None:
    with pytest.raises(ConfigError, match="ai.model"):
        OpenAIClassifier.from_config(AiConfig(enabled=True, model=None), client=object())


def test_from_config_rejects_disabled_ai() -> None:
    with pytest.raises(ConfigError, match="disabled"):
        OpenAIClassifier.from_config(AiConfig(enabled=False, model="gpt-test"), client=object())


def test_classify_new_candidate_uses_configured_model_and_schema() -> None:
    client = FakeOpenAIClient(valid_output())
    classifier = OpenAIClassifier(model="gpt-test", client=client)

    result = classifier.classify_new_candidate(watch_item(), topic_with_html_markers())

    call = client.responses.calls[0]
    assert call["model"] == "gpt-test"
    assert call["text"] == {
        "format": {
            "type": "json_schema",
            "name": "classification_result",
            "schema": classifier.response_schema,
            "strict": True,
        }
    }
    assert result.matches_watch_item is True
    assert result.listing_type == ListingType.OFFER
    assert result.availability == AvailabilityStatus.AVAILABLE


def test_classification_input_is_structured_and_does_not_send_html() -> None:
    client = FakeOpenAIClient(valid_output())
    classifier = OpenAIClassifier(model="gpt-test", client=client)

    classifier.classify_new_candidate(watch_item(), topic_with_html_markers())

    call = client.responses.calls[0]
    payload_text = str(call["input"])
    assert "watch_item" in payload_text
    assert "topic" in payload_text
    assert "2026-01-02T10:30:00Z" in payload_text
    assert "headers" not in payload_text.lower()
    assert "cookies" not in payload_text.lower()
    assert "<html" not in payload_text.lower()


def test_classify_favorite_update_includes_previous_state() -> None:
    client = FakeOpenAIClient(valid_output())
    classifier = OpenAIClassifier(model="gpt-test", client=client)
    previous = PreviousFavoriteState(
        availability=AvailabilityStatus.RESERVED,
        price=150,
        currency="EUR",
        content_hash="old-hash",
    )

    classifier.classify_favorite_update(previous, watch_item(), topic_with_html_markers())

    payload_text = str(client.responses.calls[0]["input"])
    assert "previous_state" in payload_text
    assert "old-hash" in payload_text


def test_invalid_openai_output_is_rejected() -> None:
    client = FakeOpenAIClient('{"matches_watch_item": true, "availability": "BROKEN"}')
    classifier = OpenAIClassifier(model="gpt-test", client=client)

    with pytest.raises(ValidationError):
        classifier.classify_new_candidate(watch_item(), topic_with_html_markers())
