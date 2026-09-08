"""Classification interfaces and adapters."""
"""Classification interfaces and adapters."""

from classification.base import (
    ClassificationContext,
    ClassificationPost,
    ClassificationResult,
    ListingClassifier,
    PreviousFavoriteState,
)
from classification.fake import FakeClassifier

__all__ = [
    "ClassificationContext",
    "ClassificationPost",
    "ClassificationResult",
    "FakeClassifier",
    "ListingClassifier",
    "PreviousFavoriteState",
]
