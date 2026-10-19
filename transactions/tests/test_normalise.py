import pytest

from transactions.normalise import normalise


@pytest.mark.parametrize("raw, expected", [
    ("Bol.com Purchase", "bol com purchase"),
    ("  T-Mobile   Bill  Payment ", "t mobile bill payment"),
    ("ALBERT HEIJN 1234 AMSTERDAM", "albert heijn 1234 amsterdam"),
    ("Café Loetje", "cafe loetje"),
    ("", ""),
    (None, ""),
])
def test_descriptions_normalise_to_one_form(raw, expected):
    assert normalise(raw) == expected
