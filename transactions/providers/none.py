"""What runs when no model is configured: every unknown description falls back, loudly, with the cause."""

from .base import ProviderError


class NoProvider:
    name = "none"
    version = "none@0"

    def classify(self, description):
        raise ProviderError("no model provider configured: set GEMINI_API_KEY, or CATEGORISER_PROVIDER=fake")
