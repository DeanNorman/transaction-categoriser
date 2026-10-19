"""Pick the provider from settings. `auto` means Gemini when a key is set, otherwise none."""

from django.conf import settings

from .base import Answer, InvalidAnswer, Provider, ProviderError, validate_answer
from .fake import FakeProvider
from .none import NoProvider

__all__ = ["Answer", "FakeProvider", "InvalidAnswer", "NoProvider", "Provider", "ProviderError", "get_provider", "validate_answer"]


def get_provider():
    choice = settings.CATEGORISER_PROVIDER
    if choice == "auto":
        choice = "gemini" if settings.GEMINI_API_KEY else "none"
    if choice == "fake":
        return FakeProvider()
    if choice == "none":
        return NoProvider()
    if choice == "gemini":
        from .gemini import GeminiProvider

        return GeminiProvider()
    raise ValueError(f"unknown CATEGORISER_PROVIDER {choice!r}")
