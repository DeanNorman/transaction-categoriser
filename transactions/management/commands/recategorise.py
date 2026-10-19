"""Re-run the pipeline over stored transactions: after a rules change, a new prompt version, or once a model key
exists and the fallback rows can be upgraded. manage.py recategorise [--only fallback|needs_review|all]."""

from django.core.management.base import BaseCommand

from transactions.categoriser import categorise
from transactions.models import Method, Transaction
from transactions.providers import get_provider


class Command(BaseCommand):
    help = "Re-categorise stored transactions through the current rules, cache and provider."

    def add_arguments(self, parser):
        parser.add_argument("--only", choices=["fallback", "needs_review", "all"], default="fallback",
                            help="Which rows to redo. Default: the ones that fell back.")

    def handle(self, *args, **options):
        rows = Transaction.objects.all()
        if options["only"] == "fallback":
            rows = rows.filter(method=Method.FALLBACK)
        elif options["only"] == "needs_review":
            rows = rows.filter(needs_review=True)
        provider = get_provider()
        changed = same = 0
        for record in rows.iterator():
            before = (record.category, record.method)
            categorise(record, provider)
            if (record.category, record.method) == before:
                same += 1
            else:
                changed += 1
        self.stdout.write(f"provider {provider.version}: {changed} changed, {same} unchanged, {changed + same} looked at")
