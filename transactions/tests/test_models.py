from datetime import datetime, timezone

import pytest
from django.db import IntegrityError

from transactions.categories import CATEGORY_NAMES, Category
from transactions.models import DescriptionCategory, Method, Transaction


def make(**fields):
    defaults = {
        "amount_cents": -8718,
        "timestamp": datetime(2024, 5, 16, 7, 22, 18, tzinfo=timezone.utc),
        "description": "Municipal Tax Payment",
        "transaction_type": "debit",
        "account_number": "NLINGB1944573686",
    }
    defaults.update(fields)
    return Transaction.objects.create(**defaults)


def test_there_are_exactly_the_ten_categories_from_the_brief():
    assert CATEGORY_NAMES == ["Groceries", "Dining Out", "Utilities", "Transportation", "Entertainment",
                              "Healthcare", "Shopping", "Housing", "Education", "Miscellaneous"]


@pytest.mark.django_db
def test_the_banks_id_is_the_primary_key_when_given():
    transaction = make(id="TXN00001")

    assert Transaction.objects.get(pk="TXN00001") == transaction


@pytest.mark.django_db
def test_an_id_is_generated_when_none_is_given():
    first, second = make(), make()

    assert first.id.startswith("TXN-") and len(first.id) == 12
    assert first.id != second.id


@pytest.mark.django_db
def test_amount_and_account_are_presented_safely():
    transaction = make(amount_cents=-8718, account_number="NLINGB1944573686")

    assert transaction.amount == "-87.18"
    assert transaction.masked_account == "NL******3686"


@pytest.mark.django_db
def test_a_new_transaction_is_uncategorised_until_the_pipeline_runs():
    transaction = make()

    assert (transaction.category, transaction.method, transaction.categorised_at) == (Category.MISCELLANEOUS, Method.FALLBACK, None)


@pytest.mark.django_db
def test_one_cached_decision_per_description_and_version():
    DescriptionCategory.objects.create(normalised_description="bol com purchase", version="gemini@1", category=Category.SHOPPING, confidence="0.92")
    DescriptionCategory.objects.create(normalised_description="bol com purchase", version="gemini@2", category=Category.SHOPPING, confidence="0.95")

    with pytest.raises(IntegrityError):
        DescriptionCategory.objects.create(normalised_description="bol com purchase", version="gemini@1", category=Category.SHOPPING, confidence="0.90")
