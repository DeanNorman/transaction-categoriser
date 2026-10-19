from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command

from transactions.importer import BadFile, import_csv
from transactions.models import Method, Transaction
from transactions.providers import FakeProvider

pytestmark = pytest.mark.django_db

SAMPLE = Path(settings.BASE_DIR) / "data" / "transaction_history.csv"
HEADER = "Transaction ID,Amount,Timestamp,Description,Transaction Type,Account Number\n"


def test_the_sample_file_imports_once_and_is_categorised_by_rules_alone():
    provider = FakeProvider()

    report = import_csv(SAMPLE.read_text(), provider)

    assert (report.created, report.skipped, report.rejected_count) == (1000, 0, 0)
    assert Transaction.objects.count() == 1000
    assert provider.calls == []  # every sample description is covered by a rule (decision 0004)
    assert set(Transaction.objects.values_list("method", flat=True)) == {Method.RULE}


def test_importing_the_same_file_again_creates_nothing():
    import_csv(SAMPLE.read_text(), FakeProvider())

    report = import_csv(SAMPLE.read_text(), FakeProvider())

    assert (report.created, report.skipped) == (0, 1000) and Transaction.objects.count() == 1000


def test_a_bad_row_is_rejected_with_its_line_number_and_the_rest_land():
    text = HEADER + (
        "TXN1,-10.00,2024-05-16 07:22:18,Albert Heijn Purchase,debit,NLINGB1944573686\n"
        "TXN2,ten euros,2024-05-16 07:22:18,Albert Heijn Purchase,debit,NLINGB1944573686\n"
        "TXN3,-5.00,2024-05-16 07:22:18,Rent Payment,credit,NLINGB1944573686\n"
    )

    report = import_csv(text, FakeProvider())

    assert (report.created, report.rejected_count) == (2, 1)
    assert report.rejected == [{"row": 3, "errors": {"amount": ["A valid number is required."]}}]


def test_the_same_id_twice_in_one_file_counts_as_skipped():
    text = HEADER + ("TXN1,-10.00,2024-05-16 07:22:18,Rent Payment,debit,NLINGB1944573686\n" * 2)

    report = import_csv(text, FakeProvider())

    assert (report.created, report.skipped) == (1, 1)


def test_unknown_descriptions_cost_one_provider_call_each_not_one_per_row():
    provider = FakeProvider({"*": {"category": "Dining Out", "confidence": 0.8, "reason": "a restaurant"}})
    text = HEADER + "".join(f"TXN{n},-10.00,2024-05-16 07:22:18,Ristorante Il Casale,debit,NLINGB1944573686\n" for n in range(25))

    import_csv(text, provider)

    assert provider.calls == ["Ristorante Il Casale"]
    assert Transaction.objects.filter(method=Method.MODEL).count() == 1 and Transaction.objects.filter(method=Method.CACHE).count() == 24


def test_the_wrong_columns_are_refused_before_any_row():
    with pytest.raises(BadFile, match="missing columns"):
        import_csv("id,amount\n1,2\n")


def test_the_command_imports_a_file(settings, capsys):
    settings.CATEGORISER_PROVIDER = "fake"

    call_command("import_csv", str(SAMPLE))

    assert '"created": 1000' in capsys.readouterr().out
