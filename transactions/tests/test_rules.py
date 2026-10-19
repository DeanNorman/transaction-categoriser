from decimal import Decimal

import pytest

from transactions.categories import Category
from transactions.rules import RULES, match

# Every description in the sample file, and what the rules must say about it (decisions 0002 and 0004).
SAMPLE = [
    ("Tax Refund", Category.MISCELLANEOUS),
    ("Car Lease Payment", Category.TRANSPORTATION),
    ("Municipal Tax Payment", Category.HOUSING),
    ("Albert Heijn Purchase", Category.GROCERIES),
    ("NS Train Ticket", Category.TRANSPORTATION),
    ("Transfer to ING Account", Category.MISCELLANEOUS),
    ("Payment to Ziggo", Category.UTILITIES),
    ("Payment to Rabobank", Category.MISCELLANEOUS),
    ("Netflix Subscription", Category.ENTERTAINMENT),
    ("Bunq Transfer", Category.MISCELLANEOUS),
    ("PayPal Transfer", Category.MISCELLANEOUS),
    ("Bol.com Purchase", Category.SHOPPING),
    ("Eneco Energy Bill", Category.UTILITIES),
    ("Payment to Credit Card", Category.MISCELLANEOUS),
    ("Salary from Employer", Category.MISCELLANEOUS),
    ("iDEAL Payment", Category.MISCELLANEOUS),
    ("T-Mobile Bill Payment", Category.UTILITIES),
    ("Rent Payment", Category.HOUSING),
    ("AH Online Groceries", Category.GROCERIES),
    ("Geldmaat ATM Withdrawal", Category.MISCELLANEOUS),
]


@pytest.mark.parametrize("description, category", SAMPLE)
def test_every_sample_description_is_decided_by_a_rule(description, category):
    result = match(description)

    assert result is not None, f"no rule for {description!r}"
    assert result.category == category
    assert result.reason


# One merchant per category that is not in the sample file.
UNSEEN = [
    ("Jumbo Supermarkt Utrecht", Category.GROCERIES),
    ("Thuisbezorgd.nl order 8812", Category.DINING_OUT),
    ("Vattenfall termijnbedrag", Category.UTILITIES),
    ("Shell Tankstation A2", Category.TRANSPORTATION),
    ("Spotify AB", Category.ENTERTAINMENT),
    ("Apotheek De Brug", Category.HEALTHCARE),
    ("Zalando SE", Category.SHOPPING),
    ("Hypotheek ABN AMRO", Category.HOUSING),
    ("Collegegeld UvA 2024", Category.EDUCATION),
]


@pytest.mark.parametrize("description, category", UNSEEN)
def test_plain_words_and_known_brands_cover_every_category(description, category):
    assert match(description).category == category


def test_a_mortgage_is_housing_even_when_a_bank_is_named():
    assert match("Hypotheek ABN AMRO").category == Category.HOUSING
    assert match("Payment to ABN AMRO").category == Category.MISCELLANEOUS


@pytest.mark.parametrize("description", ["Ristorante Il Casale", "XK-7731 Services BV", "Mevrouw J. de Vries"])
def test_an_unknown_merchant_has_no_rule_so_the_model_is_asked(description):
    assert match(description) is None


@pytest.mark.parametrize("description", ["Payment to Rabobank", "iDEAL Payment", "PayPal Transfer"])
def test_ambiguous_money_movement_is_marked_unsure_for_a_person(description):
    assert match(description).confidence == Decimal("0.50")


def test_rule_names_are_unique_and_confidences_are_in_range():
    names = [rule.name for rule in RULES]
    assert len(names) == len(set(names))
    assert all(Decimal("0") < rule.confidence <= Decimal("1") for rule in RULES)
