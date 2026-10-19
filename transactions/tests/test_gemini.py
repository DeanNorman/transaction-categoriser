import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from google.genai import errors

from transactions.providers import InvalidAnswer, ProviderError
from transactions.providers.gemini import ANSWER_SCHEMA, GeminiProvider


class StubClient:
    """Stands in for genai.Client: records the call, returns or raises what the test says."""

    def __init__(self, text=None, raise_=None):
        self.text, self.raise_, self.calls = text, raise_, []
        self.models = SimpleNamespace(generate_content=self.generate_content)

    def generate_content(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self.raise_:
            raise self.raise_
        return SimpleNamespace(text=self.text)


class QuotaError(errors.APIError):
    def __init__(self):
        Exception.__init__(self, "quota")
        self.code, self.message = 429, "quota exceeded"


def provider(**kwargs):
    return GeminiProvider(client=StubClient(**kwargs), model="gemini-test", timeout_seconds=3)


def test_a_good_answer_becomes_a_validated_answer():
    answer = provider(text=json.dumps({"category": "Dining Out", "confidence": 0.88, "reason": "A restaurant."})).classify("Ristorante Il Casale")

    assert (answer.category, answer.confidence, answer.reason) == ("Dining Out", Decimal("0.88"), "A restaurant.")


def test_only_the_description_is_sent_and_the_answer_shape_is_fixed(settings):
    p = provider(text=json.dumps({"category": "Housing", "confidence": 0.9, "reason": "Rent."}))

    p.classify("Rent Payment")

    call = p._client.calls[0]
    assert call["contents"] == "Rent Payment" and call["model"] == "gemini-test"
    assert call["config"].response_mime_type == "application/json"
    assert call["config"].response_json_schema == ANSWER_SCHEMA
    assert call["config"].system_instruction == p.prompt.text
    assert call["config"].temperature == 0


def test_an_answer_outside_the_ten_categories_is_invalid():
    with pytest.raises(InvalidAnswer):
        provider(text=json.dumps({"category": "Transfers", "confidence": 0.9, "reason": "x"})).classify("Bunq Transfer")


@pytest.mark.parametrize("text", ["not json at all", "", None])
def test_unreadable_output_is_invalid_not_a_crash(text):
    with pytest.raises(InvalidAnswer):
        provider(text=text).classify("something")


def test_an_api_error_is_a_provider_error_that_names_the_code():
    with pytest.raises(ProviderError, match="429"):
        provider(raise_=QuotaError()).classify("something")


def test_a_timeout_is_a_provider_error_that_names_the_class():
    with pytest.raises(ProviderError, match="TimeoutError"):
        provider(raise_=TimeoutError("read timed out")).classify("something")


def test_the_version_carries_the_model_and_the_prompt_version():
    assert provider(text="{}").version == "gemini-test@1"


def test_without_a_key_the_real_client_is_never_built(settings):
    settings.GEMINI_API_KEY = None

    with pytest.raises(ProviderError, match="GEMINI_API_KEY"):
        GeminiProvider(model="gemini-test").classify("something")
