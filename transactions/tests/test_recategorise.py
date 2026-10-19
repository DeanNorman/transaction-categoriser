from datetime import datetime, timezone

import pytest
from django.core.management import call_command

from transactions.models import Method, Transaction

pytestmark = pytest.mark.django_db


def make(description, **fields):
    defaults = {"amount_cents": -1000, "timestamp": datetime(2024, 5, 16, tzinfo=timezone.utc), "transaction_type": "debit",
                "account_number": "NLINGB1944573686", "method": Method.FALLBACK, "needs_review": True}
    defaults.update(fields)
    return Transaction.objects.create(description=description, **defaults)


def test_fallback_rows_are_upgraded_once_a_provider_exists(settings, capsys):
    settings.CATEGORISER_PROVIDER = "fake"
    make("Fietsenmaker Van Dam")  # fell back earlier: no key then
    make("Albert Heijn Purchase", method=Method.RULE, category="Groceries", needs_review=False)  # untouched by default

    call_command("recategorise")

    assert Transaction.objects.get(description="Fietsenmaker Van Dam").method == Method.MODEL
    assert "1 changed, 0 unchanged, 1 looked at" in capsys.readouterr().out


def test_all_rows_can_be_redone_after_a_rules_change(settings, capsys):
    settings.CATEGORISER_PROVIDER = "fake"
    make("Albert Heijn Purchase", method=Method.RULE, category="Shopping", needs_review=False)  # wrong under today's rules

    call_command("recategorise", only="all")

    assert Transaction.objects.get().category == "Groceries"
