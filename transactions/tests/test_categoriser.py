import logging
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from transactions.categories import Category
from transactions.categoriser import categorise, decide
from transactions.models import DescriptionCategory, Method, Transaction
from transactions.providers import FakeProvider, InvalidAnswer, NoProvider, ProviderError, get_provider, validate_answer

pytestmark = pytest.mark.django_db

SHOP = {"category": "Transportation", "confidence": 0.91, "reason": "a bicycle repair shop"}


def make(description="Fietsenmaker Van Dam", **fields):
    defaults = {"amount_cents": -12999, "timestamp": datetime(2024, 5, 16, 7, 22, tzinfo=timezone.utc),
                "transaction_type": "debit", "account_number": "NLINGB1944573686"}
    defaults.update(fields)
    return Transaction.objects.create(description=description, **defaults)


def test_a_rule_match_never_asks_the_provider():
    provider = FakeProvider()

    decision = decide("Albert Heijn Purchase", provider)

    assert (decision.category, decision.method) == (Category.GROCERIES, Method.RULE)
    assert provider.calls == []


def test_an_unknown_description_asks_the_provider_once_and_is_cached():
    provider = FakeProvider({"Ristorante Il Casale": {"category": "Dining Out", "confidence": 0.88, "reason": "an Italian restaurant"}})

    first = decide("Ristorante Il Casale", provider)
    second = decide("Ristorante Il Casale", provider)
    third = decide("  RISTORANTE IL CASALE ", provider)  # same description, different spelling

    assert (first.method, second.method, third.method) == (Method.MODEL, Method.CACHE, Method.CACHE)
    assert first.category == second.category == third.category == Category.DINING_OUT
    assert provider.calls == ["Ristorante Il Casale"]
    assert DescriptionCategory.objects.get().hits == 2


def test_the_decision_records_which_model_and_prompt_answered():
    provider = FakeProvider({"*": SHOP})
    provider.name, provider.version = "gemini-test", "gemini-test@3"

    decision = decide("Fietsenmaker Van Dam", provider)

    assert (decision.model_name, decision.prompt_version) == ("gemini-test", "3")


@pytest.mark.parametrize("bad", [
    {"category": "Transfers", "confidence": 0.9, "reason": "not one of the ten"},
    {"category": "Shopping", "confidence": 1.4, "reason": "too sure"},
    {"category": "Shopping", "confidence": "high", "reason": "not a number"},
    ["Shopping", 0.9],
])
def test_an_answer_outside_the_rules_is_a_fallback_not_a_category(bad):
    decision = decide("Fietsenmaker Van Dam", FakeProvider({"*": bad}))

    assert (decision.category, decision.method, decision.confidence) == (Category.MISCELLANEOUS, Method.FALLBACK, Decimal("0"))
    assert decision.reason.startswith("model unavailable: InvalidAnswer")
    assert DescriptionCategory.objects.count() == 0


def test_a_provider_error_is_a_fallback_that_names_the_cause():
    decision = decide("Fietsenmaker Van Dam", FakeProvider(fail_with=ProviderError("timed out after 10s")))

    assert decision.method == Method.FALLBACK
    assert decision.needs_review
    assert "timed out after 10s" in decision.reason


def test_without_a_provider_configured_the_fallback_says_how_to_fix_it():
    decision = decide("Fietsenmaker Van Dam", NoProvider())

    assert decision.method == Method.FALLBACK
    assert "GEMINI_API_KEY" in decision.reason


def test_an_empty_description_never_reaches_the_provider():
    provider = FakeProvider()

    decision = decide("   ", provider)

    assert decision.method == Method.FALLBACK and provider.calls == []


def test_low_confidence_is_flagged_for_a_person(settings):
    settings.REVIEW_THRESHOLD = 0.6

    sure = decide("Fietsenmaker Van Dam", FakeProvider({"*": SHOP}))
    unsure = decide("Mevrouw J. de Vries", FakeProvider({"*": {"category": "Shopping", "confidence": 0.4, "reason": "a guess"}}))
    rail = decide("iDEAL Payment", FakeProvider())

    assert not sure.needs_review
    assert unsure.needs_review
    assert rail.needs_review  # a rule at 0.50, below the threshold on purpose


def test_categorise_writes_the_decision_onto_the_transaction_and_saves_it():
    transaction = make()
    when = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)

    categorise(transaction, FakeProvider({"*": SHOP}), now=when)

    saved = Transaction.objects.get(pk=transaction.pk)
    assert (saved.category, saved.method, saved.confidence, saved.reason) == (Category.TRANSPORTATION, Method.MODEL, Decimal("0.91"), "a bicycle repair shop")
    assert (saved.model_name, saved.prompt_version, saved.categorised_at, saved.needs_review) == ("fake", "0", when, False)


def test_a_transaction_is_saved_even_when_the_provider_fails():
    transaction = make()

    categorise(transaction, FakeProvider(fail_with=ProviderError("quota")))

    saved = Transaction.objects.get(pk=transaction.pk)
    assert saved.method == Method.FALLBACK and saved.needs_review and saved.categorised_at is not None


def test_the_log_line_carries_ids_and_the_outcome_but_not_the_description(caplog):
    transaction = make(description="Salary from Employer", account_number="NLINGB1944573686")

    with caplog.at_level(logging.INFO, logger="transactions.categoriser"):
        categorise(transaction, FakeProvider())

    line = caplog.text
    assert transaction.id in line and "method=rule" in line
    assert "Salary" not in line and "NLINGB1944573686" not in line


def test_validate_answer_trims_the_reason_and_rounds_the_confidence():
    answer = validate_answer({"category": "Housing", "confidence": "0.955", "reason": "x" * 300})

    assert answer.confidence == Decimal("0.96") and len(answer.reason) == 200


@pytest.mark.parametrize("choice, key, expected", [("fake", None, "fake"), ("none", None, "none"), ("auto", None, "none"), ("auto", "k", "gemini-test"), ("gemini", "k", "gemini-test")])
def test_the_provider_is_chosen_from_settings(settings, choice, key, expected):
    settings.CATEGORISER_PROVIDER, settings.GEMINI_API_KEY, settings.GEMINI_MODEL = choice, key, "gemini-test"

    assert get_provider().name == expected


def test_unknown_provider_setting_is_refused(settings):
    settings.CATEGORISER_PROVIDER = "oracle"

    with pytest.raises(ValueError):
        get_provider()
