"""Classification interfaces and adapters."""

from classification.base import (
    ClassificationContext,
    ClassificationPost,
    ClassificationResult,
    ListingClassifier,
    PreviousFavoriteState,
)
from classification.fake import FakeClassifier
from classification.openai_classifier import OpenAIClassifier

__all__ = [
    "ClassificationContext",
    "ClassificationPost",
    "ClassificationResult",
    "FakeClassifier",
    "ListingClassifier",
    "OpenAIClassifier",
    "PreviousFavoriteState",
]
