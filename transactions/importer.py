"""One importer for the endpoint and the command. Rows are validated like a POST, existing IDs are skipped, bad rows
are reported with their line number, and each row is its own transaction so one failure never spoils the rest."""

import csv
import io
from dataclasses import dataclass, field

from django.db import IntegrityError, transaction as db

from .api import TransactionInputSerializer
from .categoriser import categorise
from .models import Transaction
from .money import cents_from_text

# The brief's column names -> our field names.
COLUMNS = {
    "Transaction ID": "id",
    "Amount": "amount",
    "Timestamp": "timestamp",
    "Description": "description",
    "Transaction Type": "transaction_type",
    "Account Number": "account_number",
}
REJECTED_LIMIT = 50  # how many rejected rows a report lists in full


class BadFile(ValueError):
    """The file is not a CSV in the expected layout."""


@dataclass
class Report:
    created: int = 0
    skipped: int = 0
    rejected: list = field(default_factory=list)  # [{"row": 12, "errors": {...}}], first REJECTED_LIMIT only
    rejected_count: int = 0

    def as_dict(self):
        return {"created": self.created, "skipped": self.skipped, "rejected_count": self.rejected_count, "rejected": self.rejected}


def read_rows(text):
    """CSV text -> (row number, dict in our field names). Raises BadFile on the wrong columns."""
    reader = csv.DictReader(io.StringIO(text))
    missing = [name for name in COLUMNS if name not in (reader.fieldnames or [])]
    if missing:
        raise BadFile(f"missing columns: {', '.join(missing)}")
    for number, raw in enumerate(reader, start=2):  # row 1 is the header
        yield number, {COLUMNS[name]: (raw.get(name) or "").strip() for name in COLUMNS}


def import_csv(text, provider=None):
    report = Report()
    existing = set(Transaction.objects.values_list("id", flat=True))
    for number, row in read_rows(text):
        if row["id"] in existing:
            report.skipped += 1
            continue
        incoming = TransactionInputSerializer(data=row)
        if not incoming.is_valid():
            report.rejected_count += 1
            if len(report.rejected) < REJECTED_LIMIT:
                report.rejected.append({"row": number, "errors": incoming.errors})
            continue
        fields = dict(incoming.validated_data)
        fields["amount_cents"] = cents_from_text(fields.pop("amount"))
        try:
            with db.atomic():
                record = Transaction(**fields)
                record.save(force_insert=True)
                categorise(record, provider)
        except IntegrityError:  # the same ID twice within one file
            report.skipped += 1
            continue
        existing.add(record.id)
        report.created += 1
    return report
