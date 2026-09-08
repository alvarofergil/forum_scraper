"""Structured classification contract for candidate and favorite topics."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import AvailabilityStatus, ListingType, ParsedTopic, WatchItem


class ClassificationPost(BaseModel):
    """Clean post data that may be sent to a classifier."""

    sequence_number: int
    author: str
    text: str
    external_post_id: str | None = None

    model_config = ConfigDict(frozen=True)


class ClassificationContext(BaseModel):
    """Clean structured topic data prepared for classification."""

    watch_item_id: str
    watch_item_brand: str
    watch_item_model: str
    watch_item_aliases: tuple[str, ...] = ()
    external_topic_id: str
    topic_title: str
    original_author: str
    posts: tuple[ClassificationPost, ...]

    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_topic(cls, watch_item: WatchItem, topic: ParsedTopic) -> ClassificationContext:
        """Build classifier input from parsed domain models without HTML or headers."""

        return cls(
            watch_item_id=watch_item.id,
            watch_item_brand=watch_item.brand,
            watch_item_model=watch_item.model,
            watch_item_aliases=watch_item.aliases,
            external_topic_id=topic.external_topic_id,
            topic_title=topic.topic_title,
            original_author=topic.original_author,
            posts=tuple(
                ClassificationPost(
                    sequence_number=post.sequence_number,
                    author=post.author,
                    text=post.text,
                    external_post_id=post.external_post_id,
                )
                for post in topic.posts
            ),
        )


class PreviousFavoriteState(BaseModel):
    """Current favorite state supplied when classifying an update."""

    availability: AvailabilityStatus
    price: float | None = None
    currency: str | None = None
    content_hash: str | None = None

    model_config = ConfigDict(frozen=True, use_enum_values=False)

    @field_validator("price")
    @classmethod
    def _price_must_not_be_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("price must be greater than or equal to 0")
        return value


class ClassificationResult(BaseModel):
    """Validated classifier decision consumed by later services."""

    matches_watch_item: bool
    listing_type: ListingType
    availability: AvailabilityStatus
    price: float | None = None
    currency: str | None = None
    confidence: float = Field(ge=0, le=1)
    evidence: tuple[str, ...] = ()

    model_config = ConfigDict(frozen=True, use_enum_values=False)

    @field_validator("price")
    @classmethod
    def _price_must_not_be_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("price must be greater than or equal to 0")
        return value


class ListingClassifier(Protocol):
    """Classifier interface shared by fake, OpenAI and future adapters."""

    def classify_new_candidate(
        self,
        watch_item: WatchItem,
        topic: ParsedTopic,
    ) -> ClassificationResult:
        """Classify a newly discovered candidate topic."""

    def classify_favorite_update(
        self,
        previous_state: PreviousFavoriteState,
        watch_item: WatchItem,
        topic: ParsedTopic,
    ) -> ClassificationResult:
        """Classify a changed already-favorited topic."""
