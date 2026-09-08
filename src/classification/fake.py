"""Deterministic fake classifier for unit tests."""

from __future__ import annotations

from app.models import AvailabilityStatus, ListingType, ParsedTopic, WatchItem
from classification.base import ClassificationResult, PreviousFavoriteState


class FakeClassifier:
    """Return configured classifier results and record calls."""

    def __init__(
        self,
        *,
        new_candidate_results: dict[tuple[str, str], ClassificationResult] | None = None,
        favorite_update_results: dict[tuple[str, str], ClassificationResult] | None = None,
        default_result: ClassificationResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._new_candidate_results = new_candidate_results or {}
        self._favorite_update_results = favorite_update_results or {}
        self._default_result = default_result or ClassificationResult(
            matches_watch_item=False,
            listing_type=ListingType.OTHER,
            availability=AvailabilityStatus.UNKNOWN,
            price=None,
            currency=None,
            confidence=0,
        )
        self._new_candidate_calls: list[tuple[WatchItem, ParsedTopic]] = []
        self._favorite_update_calls: list[tuple[PreviousFavoriteState, WatchItem, ParsedTopic]] = []
        self._error = error

    @property
    def new_candidate_calls(self) -> tuple[tuple[WatchItem, ParsedTopic], ...]:
        """Calls made to classify newly discovered candidates."""

        return tuple(self._new_candidate_calls)

    @property
    def favorite_update_calls(
        self,
    ) -> tuple[tuple[PreviousFavoriteState, WatchItem, ParsedTopic], ...]:
        """Calls made to classify favorite updates."""

        return tuple(self._favorite_update_calls)

    def classify_new_candidate(
        self,
        watch_item: WatchItem,
        topic: ParsedTopic,
    ) -> ClassificationResult:
        """Return a configured new-candidate result or the safe default."""

        self._new_candidate_calls.append((watch_item, topic))
        if self._error is not None:
            raise self._error
        return self._new_candidate_results.get(
            (watch_item.id, topic.external_topic_id),
            self._default_result,
        )

    def classify_favorite_update(
        self,
        previous_state: PreviousFavoriteState,
        watch_item: WatchItem,
        topic: ParsedTopic,
    ) -> ClassificationResult:
        """Return a configured favorite-update result or the safe default."""

        self._favorite_update_calls.append((previous_state, watch_item, topic))
        if self._error is not None:
            raise self._error
        return self._favorite_update_results.get(
            (watch_item.id, topic.external_topic_id),
            self._default_result,
        )
