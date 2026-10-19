"""Try the pipeline on any text, from the command line: manage.py decide "Fietsenmaker Van Dam"."""

import json
from dataclasses import asdict

from django.core.management.base import BaseCommand

from transactions.categoriser import decide
from transactions.providers import get_provider


class Command(BaseCommand):
    help = "Categorise one description and print the decision as JSON."

    def add_arguments(self, parser):
        parser.add_argument("description")

    def handle(self, *args, **options):
        provider = get_provider()
        decision = decide(options["description"], provider)
        out = asdict(decision)
        out["confidence"] = str(decision.confidence)
        out["needs_review"] = decision.needs_review
        out["provider"] = provider.version
        self.stdout.write(json.dumps(out, indent=2))
