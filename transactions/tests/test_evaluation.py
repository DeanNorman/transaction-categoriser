from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command

from transactions.evaluation import evaluate, read_gold
from transactions.providers import FakeProvider, NoProvider

pytestmark = pytest.mark.django_db

GOLD = read_gold((Path(settings.BASE_DIR) / "data" / "gold.csv").read_text())


def test_the_gold_set_covers_every_category_and_the_whole_sample():
    categories = {row["category"] for row in GOLD}
    sample_rows = [row for row in GOLD if row["source"] == "sample"]

    assert len(categories) == 10
    assert len(sample_rows) == 20


def test_rules_alone_get_every_sample_row_right_and_say_where_they_are_blind():
    result = evaluate(GOLD, NoProvider())

    assert result.by_source["sample"] == [20, 20]
    assert result.by_method["fallback"][1] > 0  # the rows no rule knows: that is the model's job
    assert all(m.method == "fallback" for m in result.misses if m.expected != "Miscellaneous")


def test_a_provider_that_knows_the_answers_closes_the_gap():
    answers = {row["description"]: {"category": row["category"], "confidence": 0.85, "reason": "scripted"} for row in GOLD}

    result = evaluate(GOLD, FakeProvider(answers))

    assert result.accuracy == 1.0 and result.misses == []


def test_misses_are_listed_with_what_was_expected_and_what_came_back():
    rows = [{"description": "Fietsenmaker Van Dam", "category": "Transportation", "source": "edge"}]

    result = evaluate(rows, FakeProvider({"*": {"category": "Shopping", "confidence": 0.7, "reason": "a shop, guessed"}}))

    assert result.accuracy == 0.0
    miss = result.misses[0]
    assert (miss.expected, miss.got, miss.method, str(miss.confidence)) == ("Transportation", "Shopping", "model", "0.70")
    assert "| Fietsenmaker Van Dam | Transportation | Shopping |" in result.to_markdown("t")


def test_the_command_prints_a_markdown_report(settings, capsys):
    call_command("evaluate", provider="none")

    out = capsys.readouterr().out
    assert out.startswith("## Rules plus provider `none@0`") and "| rule |" in out
