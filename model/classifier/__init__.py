"""
Two-Class AI Call Transcript Intent Classifier.
Industry-agnostic classifier determining customer intent: INTERESTED vs NOT_INTERESTED.
"""

from .models import (
    IntentClassification,
    StrictClassificationResponse,
    DetailedClassificationResponse,
    Turn,
    SpeakerRole,
)
from .engine import IntentClassifier

__all__ = [
    "IntentClassification",
    "StrictClassificationResponse",
    "DetailedClassificationResponse",
    "Turn",
    "SpeakerRole",
    "IntentClassifier",
]
