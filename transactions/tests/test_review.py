import pytest
from rest_framework.test import APIClient

from transactions.categories import CATEGORY_NAMES
from transactions.importer import import_csv
from transactions.providers import FakeProvider

pytestmark = pytest.mark.django_db

HEADER = "Transaction ID,Amount,Timestamp,Description,Transaction Type,Account Number\n"
ROWS = HEADER + (
    "A,-32.10,2024-05-10 09:00:00,Albert Heijn Purchase,debit,NLINGB1944573686\n"
    "B,-15.00,2024-05-11 09:00:00,iDEAL Payment,debit,NLINGB1944573686\n"
    "C,-950.00,2024-06-01 09:00:00,Rent Payment,debit,NLRABO0000000001\n"
)


@pytest.fixture
def loaded(settings):
    settings.CATEGORISER_PROVIDER = "fake"
    import_csv(ROWS, FakeProvider())
    return APIClient()


def test_the_page_shows_every_row_with_its_reason_and_flags(loaded):
    html = loaded.get("/review").content.decode()

    assert "Albert Heijn Purchase" in html and "Albert Heijn is a supermarket" in html
    assert html.count("needs a look") >= 2  # the KPI and the flagged iDEAL row
    assert "NLINGB1944573686" not in html  # no account numbers on the page


def test_the_page_renders_without_data_and_says_how_to_get_some(db):
    html = APIClient().get("/review").content.decode()

    assert "No transactions yet" in html and "import_csv" in html


def test_a_filter_narrows_the_rows_and_the_counts_stay_whole(loaded):
    html = loaded.get("/review?category=Housing").content.decode()

    assert "Rent Payment" in html and "Albert Heijn Purchase" not in html
    assert "1 of 3 shown" in html


def test_a_bad_filter_is_explained_not_ignored(loaded):
    html = loaded.get("/review?category=Transfers").content.decode()

    assert "not understood" in html and "0 of 3 shown" in html


def test_categories_endpoint_covers_all_ten_and_sums_to_the_total(loaded):
    counts = loaded.get("/categories").json()

    assert [c["category"] for c in counts] == CATEGORY_NAMES
    assert sum(c["count"] for c in counts) == 3
    assert next(c for c in counts if c["category"] == "Miscellaneous") == {"category": "Miscellaneous", "count": 1, "needs_review": 1}
