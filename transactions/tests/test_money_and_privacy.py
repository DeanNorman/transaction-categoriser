import pytest

from transactions.money import cents_from_text, text_from_cents
from transactions.privacy import mask_account


@pytest.mark.parametrize("text, cents", [("-87.18", -8718), ("473.45", 47345), ("42.6", 4260), ("0.05", 5), ("12,50", 1250), (" 7 ", 700)])
def test_amounts_become_integer_cents(text, cents):
    assert cents_from_text(text) == cents


def test_half_a_cent_rounds_up_not_to_even():
    assert cents_from_text("0.125") == 13


@pytest.mark.parametrize("bad", ["abc", "", "1.2.3", "NaN", "inf"])
def test_anything_that_is_not_an_amount_is_refused(bad):
    with pytest.raises(ValueError):
        cents_from_text(bad)


@pytest.mark.parametrize("cents, text", [(-8718, "-87.18"), (5, "0.05"), (0, "0.00"), (123400, "1234.00")])
def test_cents_become_decimal_strings(cents, text):
    assert text_from_cents(cents) == text


def test_account_numbers_are_masked_to_two_and_four():
    assert mask_account("NLINGB1944573686") == "NL******3686"
    assert mask_account("NL91ABNA0417164300") == "NL******4300"


def test_a_short_or_empty_account_number_is_fully_masked():
    assert mask_account("123456") == "******"
    assert mask_account("") == ""
