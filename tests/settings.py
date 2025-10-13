from __future__ import annotations

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "mcp_django",
    "tests",
]

ROOT_URLCONF = "tests.urls"

SECRET_KEY = "test-secret-key"

USE_TZ = True
