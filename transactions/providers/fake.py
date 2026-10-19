"""A provider for tests and for running without a key. It answers from a script and records every call."""

from .base import validate_answer

DEFAULT = {"category": "Miscellaneous", "confidence": 0.5, "reason": "fake provider: no scripted answer"}


class FakeProvider:
    name = "fake"
    version = "fake@0"

    def __init__(self, answers=None, fail_with=None):
        self.answers = dict(answers or {})  # description -> raw answer dict; "*" is the default
        self.fail_with = fail_with  # an exception instance to raise on every call
        self.calls = []

    def classify(self, description):
        self.calls.append(description)
        if self.fail_with is not None:
            raise self.fail_with
        return validate_answer(self.answers.get(description, self.answers.get("*", DEFAULT)))
