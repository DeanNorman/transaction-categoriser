"""Gemini through google-genai: JSON in a fixed shape, a time limit, and every failure named (decision 0002).
Only the description is sent (decision 0005)."""

import json

from django.conf import settings

from ..categories import CATEGORY_NAMES
from ..prompt import load_prompt
from .base import InvalidAnswer, ProviderError, validate_answer

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORY_NAMES},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reason": {"type": "string"},
    },
    "required": ["category", "confidence", "reason"],
}


class GeminiProvider:
    def __init__(self, client=None, model=None, timeout_seconds=None, prompt=None):
        self.model = model or settings.GEMINI_MODEL
        self.prompt = prompt or load_prompt()
        self.timeout_seconds = float(timeout_seconds or settings.CATEGORISER_TIMEOUT_SECONDS)
        self._client = client

    @property
    def name(self):
        return self.model

    @property
    def version(self):
        return f"{self.model}@{self.prompt.version}"

    @property
    def client(self):
        if self._client is None:
            if not settings.GEMINI_API_KEY:
                raise ProviderError("GEMINI_API_KEY is not set")
            from google import genai
            from google.genai import types

            self._client = genai.Client(
                api_key=settings.GEMINI_API_KEY,
                http_options=types.HttpOptions(timeout=int(self.timeout_seconds * 1000)),
            )
        return self._client

    def config(self):
        from google.genai import types

        thinking = {}
        if self.model.startswith("gemini-2.5"):
            thinking["thinking_config"] = types.ThinkingConfig(thinking_budget=0)  # classification needs no deliberation
        return types.GenerateContentConfig(
            system_instruction=self.prompt.text,
            response_mime_type="application/json",
            response_json_schema=ANSWER_SCHEMA,
            temperature=0,
            max_output_tokens=200,
            **thinking,
        )

    def classify(self, description):
        from google.genai import errors

        try:
            response = self.client.models.generate_content(model=self.model, contents=description, config=self.config())
        except errors.APIError as error:
            raise ProviderError(f"Gemini API error {getattr(error, 'code', '?')}: {getattr(error, 'message', error)}") from error
        except ProviderError:
            raise
        except Exception as error:  # a timeout or a network failure: name it, fall back
            raise ProviderError(f"{type(error).__name__}: {error}") from error

        text = (response.text or "").strip()
        if not text:
            raise InvalidAnswer("empty answer from the model")
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as error:
            raise InvalidAnswer(f"answer is not JSON: {text[:60]!r}") from error
        return validate_answer(raw)
