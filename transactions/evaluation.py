"""Score the pipeline against a hand-labelled gold set. Pure: give it rows and a provider, get numbers back."""

import csv
import io
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from .categoriser import decide
from .models import Method


@dataclass
class Miss:
    description: str
    expected: str
    got: str
    method: str
    confidence: Decimal
    reason: str


@dataclass
class Result:
    total: int = 0
    correct: int = 0
    by_method: dict = field(default_factory=lambda: defaultdict(lambda: [0, 0]))  # method -> [correct, total]
    by_category: dict = field(default_factory=lambda: defaultdict(lambda: [0, 0]))  # expected -> [correct, total]
    by_source: dict = field(default_factory=lambda: defaultdict(lambda: [0, 0]))  # sample/edge -> [correct, total]
    confidence_when_right: list = field(default_factory=list)
    confidence_when_wrong: list = field(default_factory=list)
    misses: list = field(default_factory=list)

    @property
    def accuracy(self):
        return self.correct / self.total if self.total else 0.0

    def to_markdown(self, title):
        lines = [f"## {title}", "", f"**{self.correct} of {self.total} right ({self.accuracy:.0%}).**", ""]
        lines += ["| Decided by | Right | Of |", "|---|---|---|"]
        for method, (right, total) in sorted(self.by_method.items()):
            lines.append(f"| {method} | {right} | {total} |")
        lines += ["", "| Rows | Right | Of |", "|---|---|---|"]
        for source, (right, total) in sorted(self.by_source.items()):
            lines.append(f"| {source} | {right} | {total} |")
        lines += ["", "| Expected category | Right | Of |", "|---|---|---|"]
        for category, (right, total) in sorted(self.by_category.items()):
            lines.append(f"| {category} | {right} | {total} |")
        mean = lambda xs: (sum(xs) / len(xs)) if xs else Decimal(0)
        lines += ["", f"Mean confidence when right: {mean(self.confidence_when_right):.2f}; when wrong: {mean(self.confidence_when_wrong):.2f}.", ""]
        if self.misses:
            lines += ["| Description | Expected | Got | By | Confidence | Reason |", "|---|---|---|---|---|---|"]
            for m in self.misses:
                lines.append(f"| {m.description} | {m.expected} | {m.got} | {m.method} | {m.confidence} | {m.reason} |")
        else:
            lines.append("No misses.")
        return "\n".join(lines) + "\n"


def read_gold(text):
    rows = list(csv.DictReader(io.StringIO(text)))
    for required in ("description", "category"):
        if rows and required not in rows[0]:
            raise ValueError(f"gold set has no '{required}' column")
    return rows


def evaluate(rows, provider):
    result = Result()
    for row in rows:
        expected, source = row["category"], row.get("source") or "all"
        decision = decide(row["description"], provider)
        right = decision.category == expected
        result.total += 1
        result.correct += right
        for bucket, key in ((result.by_method, decision.method), (result.by_category, expected), (result.by_source, source)):
            bucket[key][0] += right
            bucket[key][1] += 1
        (result.confidence_when_right if right else result.confidence_when_wrong).append(decision.confidence)
        if not right:
            result.misses.append(Miss(row["description"], expected, decision.category, decision.method, decision.confidence, decision.reason))
    return result
