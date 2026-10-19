"""Money is integer cents everywhere inside; decimal strings at the edges (decision 0003)."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")


def cents_from_text(value):
    """'-87.18' -> -8718. Anything that is not a decimal number is a ValueError, never a silent 0."""
    try:
        amount = Decimal(str(value).strip().replace(",", "."))
    except InvalidOperation as error:
        raise ValueError(f"not an amount: {value!r}") from error
    if not amount.is_finite():
        raise ValueError(f"not an amount: {value!r}")
    return int(amount.quantize(CENT, rounding=ROUND_HALF_UP) * 100)


def text_from_cents(cents):
    """-8718 -> '-87.18'; 5 -> '0.05'."""
    return str((Decimal(cents) / 100).quantize(CENT))
