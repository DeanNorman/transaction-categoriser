"""manage.py evaluate [--gold data/gold.csv] [--provider auto|fake|none|gemini]: prints a markdown report."""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from transactions.evaluation import evaluate, read_gold
from transactions.providers import get_provider


class Command(BaseCommand):
    help = "Score the categoriser against the hand-labelled gold set and print a markdown report."

    def add_arguments(self, parser):
        parser.add_argument("--gold", default=str(Path(settings.BASE_DIR) / "data" / "gold.csv"))
        parser.add_argument("--provider", default=None, help="Override CATEGORISER_PROVIDER for this run.")

    def handle(self, *args, **options):
        path = Path(options["gold"])
        if not path.is_file():
            raise CommandError(f"no such file: {path}")
        if options["provider"]:
            settings.CATEGORISER_PROVIDER = options["provider"]
        provider = get_provider()
        result = evaluate(read_gold(path.read_text(encoding="utf-8-sig")), provider)
        self.stdout.write(result.to_markdown(f"Rules plus provider `{provider.version}`"))
