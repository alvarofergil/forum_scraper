"""OpenAI-backed classifier adapter using structured outputs."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from app.config import AiConfig, ConfigError
from app.models import AvailabilityStatus, ListingType, ParsedTopic, WatchItem
from classification.base import (
    ClassificationContext,
    ClassificationResult,
    PreviousFavoriteState,
)


class OpenAIClassifier:
    """Classify forum topics through an injected or lazily-created OpenAI client."""

    response_schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "matches_watch_item": {"type": "boolean"},
            "listing_type": {"type": "string", "enum": [item.value for item in ListingType]},
            "availability": {
                "type": "string",
                "enum": [item.value for item in AvailabilityStatus],
            },
            "price": {"type": ["number", "null"]},
            "currency": {"type": ["string", "null"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "evidence": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "matches_watch_item",
            "listing_type",
            "availability",
            "price",
            "currency",
            "confidence",
            "evidence",
        ],
    }

    def __init__(self, *, model: str, client: Any | None = None) -> None:
        if not model.strip():
            raise ConfigError("ai.model must be configured when ai.enabled=true")
        self.model = model.strip()
        self._client = client

    @classmethod
    def from_config(cls, ai: AiConfig, *, client: Any | None = None) -> OpenAIClassifier:
        """Create the adapter from validated AI config."""

        if not ai.enabled:
            raise ConfigError("AI classification is disabled by ai.enabled=false")
        if ai.model is None:
            raise ConfigError("ai.model must be configured when ai.enabled=true")
        return cls(model=ai.model, client=client)

    def classify_new_candidate(
        self,
        watch_item: WatchItem,
        topic: ParsedTopic,
    ) -> ClassificationResult:
        """Classify a newly discovered candidate topic."""

        payload = {
            "task": "classify_new_candidate",
            "watch_item": self._watch_item_payload(watch_item),
            "topic": ClassificationContext.from_topic(watch_item, topic).model_dump(mode="json"),
        }
        return self._classify(payload)

    def classify_favorite_update(
        self,
        previous_state: PreviousFavoriteState,
        watch_item: WatchItem,
        topic: ParsedTopic,
    ) -> ClassificationResult:
        """Classify a changed already-favorited topic."""

        payload = {
            "task": "classify_favorite_update",
            "watch_item": self._watch_item_payload(watch_item),
            "previous_state": previous_state.model_dump(mode="json"),
            "topic": ClassificationContext.from_topic(watch_item, topic).model_dump(mode="json"),
        }
        return self._classify(payload)

    def _classify(self, payload: dict[str, Any]) -> ClassificationResult:
        response = self._client_or_default().responses.create(
            model=self.model,
            input=[
                {
                    "role": "developer",
                    "content": (
                        "Return only a structured classification result for the supplied "
                        "clean forum topic data. Do not infer from unavailable HTML."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        self._strip_html_markers(payload),
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "classification_result",
                    "schema": self.response_schema,
                    "strict": True,
                }
            },
        )
        return self._parse_response(response)

    def _client_or_default(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ConfigError("openai package is required when ai.enabled=true") from exc

        self._client = OpenAI()
        return self._client

    @staticmethod
    def _parse_response(response: Any) -> ClassificationResult:
        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise ConfigError("OpenAI response did not contain output_text")
        try:
            data = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ConfigError("OpenAI response was not valid JSON") from exc
        try:
            return ClassificationResult.model_validate(data)
        except ValidationError as exc:
            raise ConfigError("OpenAI response did not match classification schema") from exc

    @staticmethod
    def _watch_item_payload(watch_item: WatchItem) -> dict[str, object]:
        return {
            "id": watch_item.id,
            "brand": watch_item.brand,
            "model": watch_item.model,
            "aliases": list(watch_item.aliases),
        }

    @classmethod
    def _strip_html_markers(cls, value: Any) -> Any:
        if isinstance(value, str):
            return re.sub(r"<[^>]*>", "", value)
        if isinstance(value, list):
            return [cls._strip_html_markers(item) for item in value]
        if isinstance(value, tuple):
            return tuple(cls._strip_html_markers(item) for item in value)
        if isinstance(value, dict):
            return {key: cls._strip_html_markers(item) for key, item in value.items()}
        return value
