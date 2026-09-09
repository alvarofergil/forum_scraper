from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

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


def topic_with_two_ordered_posts() -> ParsedTopic:
    return ParsedTopic(
        topic_title="Vendo Acme Target Pro",
        external_topic_id="123",
        original_author="seller_001",
        total_posts=2,
        current_page=1,
        total_pages=1,
        posts=(
            TopicPost(
                sequence_number=1,
                author="seller_001",
                posted_at=datetime(2026, 1, 2, 10, 30, tzinfo=UTC),
                text="Primer mensaje limpio",
                external_post_id="456",
            ),
            TopicPost(
                sequence_number=2,
                author="buyer_001",
                posted_at=datetime(2026, 1, 2, 11, 0, tzinfo=UTC),
                text="Segundo mensaje limpio",
                external_post_id="789",
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


def test_openai_classifier_uses_strict_supported_schema() -> None:
    client = FakeOpenAIClient(valid_output())
    classifier = OpenAIClassifier(model="gpt-test", client=client)

    classifier.classify_new_candidate(watch_item(), topic_with_html_markers())

    call = client.responses.calls[0]
    text_format = call["text"]["format"]
    schema = text_format["schema"]
    assert text_format["strict"] is True
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "matches_watch_item",
        "listing_type",
        "availability",
        "price",
        "currency",
        "confidence",
        "evidence",
    }
    assert schema["properties"]["price"]["type"] == ["number", "null"]
    assert schema["properties"]["currency"]["type"] == ["string", "null"]
    assert schema["properties"]["evidence"]["type"] == "array"


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


def test_classification_input_preserves_original_author_dates_and_post_order() -> None:
    client = FakeOpenAIClient(valid_output())
    classifier = OpenAIClassifier(model="gpt-test", client=client)

    classifier.classify_new_candidate(watch_item(), topic_with_two_ordered_posts())

    user_message = client.responses.calls[0]["input"][1]
    payload = json.loads(user_message["content"])
    posts = payload["topic"]["posts"]
    assert payload["topic"]["original_author"] == "seller_001"
    assert [post["sequence_number"] for post in posts] == [1, 2]
    assert [post["posted_at"] for post in posts] == [
        "2026-01-02T10:30:00Z",
        "2026-01-02T11:00:00Z",
    ]


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


def test_openai_classifier_rejects_invalid_output_without_leaking_raw_response() -> None:
    raw_response = (
        '{"matches_watch_item": true, "availability": "BROKEN", '
        '"evidence": ["very long third party response"]}'
    )
    client = FakeOpenAIClient(raw_response)
    classifier = OpenAIClassifier(model="gpt-test", client=client)

    with pytest.raises(ConfigError) as exc_info:
        classifier.classify_new_candidate(watch_item(), topic_with_html_markers())

    assert "did not match classification schema" in str(exc_info.value)
    assert "BROKEN" not in str(exc_info.value)
    assert "very long third party response" not in str(exc_info.value)
