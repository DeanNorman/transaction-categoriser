"""The pipeline (decision 0002): rules, then the cache, then the provider, then the fallback. Every decision says
how it was made. A provider problem never loses a transaction."""

import logging
import time
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.db.models import F
from django.utils import timezone

from . import rules
from .categories import Category
from .models import DescriptionCategory, Method
from .normalise import normalise
from .providers import ProviderError, get_provider

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Decision:
    category: str
    confidence: Decimal
    method: str
    reason: str
    model_name: str = ""
    prompt_version: str = ""

    @property
    def needs_review(self):
        return self.method == Method.FALLBACK or self.confidence < Decimal(str(settings.REVIEW_THRESHOLD))


def fallback(cause):
    return Decision(Category.MISCELLANEOUS, Decimal("0.00"), Method.FALLBACK, f"model unavailable: {cause}"[:200])


def decide(description, provider=None):
    """A Decision for one description, without touching any transaction."""
    normalised = normalise(description)
    if not normalised:
        return fallback("empty description")

    matched = rules.match(description)
    if matched:
        return Decision(matched.category, matched.confidence, Method.RULE, matched.reason)

    provider = provider or get_provider()
    model_name, prompt_version = provider.name, provider.version.split("@", 1)[-1]

    cached = DescriptionCategory.objects.filter(normalised_description=normalised, version=provider.version).first()
    if cached:
        DescriptionCategory.objects.filter(pk=cached.pk).update(hits=F("hits") + 1)
        return Decision(cached.category, cached.confidence, Method.CACHE, cached.reason, model_name, prompt_version)

    try:
        answer = provider.classify(description)
    except ProviderError as error:
        return fallback(f"{type(error).__name__}: {error}")

    DescriptionCategory.objects.get_or_create(
        normalised_description=normalised,
        version=provider.version,
        defaults={"category": answer.category, "confidence": answer.confidence, "reason": answer.reason},
    )
    return Decision(answer.category, answer.confidence, Method.MODEL, answer.reason, model_name, prompt_version)


def categorise(transaction, provider=None, now=None):
    """Decide, write the decision onto the transaction, save, and log the outcome (IDs and outcome only)."""
    started = time.perf_counter()
    decision = decide(transaction.description, provider)
    transaction.category = decision.category
    transaction.confidence = decision.confidence
    transaction.method = decision.method
    transaction.reason = decision.reason
    transaction.model_name = decision.model_name
    transaction.prompt_version = decision.prompt_version
    transaction.needs_review = decision.needs_review
    transaction.categorised_at = now or timezone.now()
    transaction.save()
    log.info(
        "categorised id=%s method=%s category=%s confidence=%s review=%s ms=%d",
        transaction.id, decision.method, decision.category, decision.confidence, decision.needs_review,
        (time.perf_counter() - started) * 1000,
    )
    return transaction
