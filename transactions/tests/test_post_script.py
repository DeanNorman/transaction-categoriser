import sys
from pathlib import Path

import pytest
from django.conf import settings

sys.path.insert(0, str(Path(settings.BASE_DIR) / "scripts"))
import post_transactions  # noqa: E402

HEADER = "Transaction ID,Amount,Timestamp,Description,Transaction Type,Account Number\n"


@pytest.mark.django_db(transaction=True)
def test_the_script_posts_each_row_through_the_api_and_reports(live_server, tmp_path, settings):
    settings.CATEGORISER_PROVIDER = "fake"
    path = tmp_path / "history.csv"
    path.write_text(HEADER + (
        "TXN1,-32.10,2024-05-10 09:00:00,Albert Heijn Purchase,debit,NLINGB1944573686\n"
        "TXN1,-32.10,2024-05-10 09:00:00,Albert Heijn Purchase,debit,NLINGB1944573686\n"
        "TXN2,ten euros,2024-05-11 09:00:00,Rent Payment,debit,NLINGB1944573686\n"
        "TXN3,-950.00,2024-06-01 09:00:00,Rent Payment,debit,NLRABO0000000001\n"
    ))
    lines = []

    report = post_transactions.post_file(path, live_server.url, log=lines.append)

    assert (report["created"], report["conflicts"], report["rejected"], report["failed"]) == (2, 1, 1, 0)
    assert report["rejected_rows"] == [{"row": 4, "errors": {"amount": ["A valid number is required."]}}]
    assert lines[0].startswith("row 2: TXN1 -> Groceries (rule, 0.98)")


def test_the_wrong_columns_stop_before_any_request(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("id,amount\n1,2\n")

    with pytest.raises(SystemExit, match="missing columns"):
        list(post_transactions.rows_from(path))
