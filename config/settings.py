"""Settings come from the environment. Defaults are for local development and tests; Compose sets the rest."""

import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=None):
    value = os.environ.get(name)
    return default if value in (None, "") else value


def env_bool(name, default=False):
    return str(env(name, default)).lower() in ("1", "true", "yes", "on")


SECRET_KEY = env("SECRET_KEY", "dev-only-not-a-secret")
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = env("ALLOWED_HOSTS", "localhost,127.0.0.1,web").split(",")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "transactions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
    }
]


def database_from_url(url):
    """postgres://user:password@host:5432/name -> Django settings. No URL means SQLite, for local tests."""
    if not url:
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
    parts = urlparse(url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parts.path.lstrip("/"),
        "USER": parts.username,
        "PASSWORD": parts.password,
        "HOST": parts.hostname,
        "PORT": parts.port or 5432,
        "CONN_MAX_AGE": 60,
    }


DATABASES = {"default": database_from_url(env("DATABASE_URL"))}

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/Amsterdam"  # timestamps without a zone are read in this zone (decision 0003)
USE_I18N = False
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser", "rest_framework.parsers.MultiPartParser"],
    "UNAUTHENTICATED_USER": None,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Transaction categorisation API",
    "DESCRIPTION": "Submit banking transactions; get them back in one of ten categories, with the reason.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Categorisation (decision 0002)
CATEGORISER_PROVIDER = env("CATEGORISER_PROVIDER", "auto")  # auto | gemini | none | fake
GEMINI_API_KEY = env("GEMINI_API_KEY")
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-2.5-flash")
CATEGORISER_TIMEOUT_SECONDS = float(env("CATEGORISER_TIMEOUT_SECONDS", 10))
REVIEW_THRESHOLD = float(env("REVIEW_THRESHOLD", 0.6))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}
