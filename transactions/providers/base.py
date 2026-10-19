"""The seam between the pipeline and any model. A provider answers with a category, a confidence and a reason;
the pipeline trusts none of it until `validate_answer` has checked it (decision 0002)."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Protocol

from ..categories import CATEGORY_NAMES

REASON_LIMIT = 200


class ProviderError(Exception):
    """The provider could not answer: no key, network, timeout, quota, unreadable output."""


class InvalidAnswer(ProviderError):
    """The provider answered, but outside the rules: unknown category, confidence out of range."""


@dataclass(frozen=True)
class Answer:
    category: str
    confidence: Decimal
    reason: str


class Provider(Protocol):
    name: str  # what to record as the model, e.g. "gemini-2.5-flash"
    version: str  # the cache key: "<name>@<prompt version>"

    def classify(self, description: str) -> Answer: ...


def validate_answer(raw):
    """A dict from a model -> Answer, or InvalidAnswer. The category must be one of the ten; the confidence a number
    in [0, 1]; the reason is cut to 200 characters."""
    if not isinstance(raw, dict):
        raise InvalidAnswer(f"answer is not an object but {type(raw).__name__}")
    category = raw.get("category")
    if category not in CATEGORY_NAMES:
        raise InvalidAnswer(f"unknown category {category!r}")
    try:
        confidence = Decimal(str(raw.get("confidence")))
    except InvalidOperation as error:
        raise InvalidAnswer(f"confidence is not a number: {raw.get('confidence')!r}") from error
    if not confidence.is_finite() or not Decimal(0) <= confidence <= Decimal(1):
        raise InvalidAnswer(f"confidence out of range: {confidence}")
    reason = str(raw.get("reason") or "").strip()[:REASON_LIMIT]
    return Answer(category, confidence.quantize(Decimal("0.01")), reason)
