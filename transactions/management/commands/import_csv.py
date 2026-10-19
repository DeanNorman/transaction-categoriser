"""manage.py import_csv data/transaction_history.csv: the same importer the endpoint uses."""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from transactions.importer import BadFile, import_csv


class Command(BaseCommand):
    help = "Import a CSV of transactions in the brief's layout. Existing IDs are skipped; bad rows are reported."

    def add_arguments(self, parser):
        parser.add_argument("path")

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.is_file():
            raise CommandError(f"no such file: {path}")
        try:
            report = import_csv(path.read_text(encoding="utf-8-sig"))
        except BadFile as error:
            raise CommandError(str(error)) from error
        self.stdout.write(json.dumps(report.as_dict(), indent=2))
