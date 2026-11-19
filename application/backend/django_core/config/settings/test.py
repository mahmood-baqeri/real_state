# Path: backend/django_core/config/settings/test.py

import os
from .base import *  # noqa: F401, F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

if "TEST_DATABASE_URL" in os.environ:
    DATABASES = {"default": parse_database_url(os.environ["TEST_DATABASE_URL"])}
elif os.environ.get("USE_LOCAL_SANDBOX_DB", "1") == "1" and "DATABASE_URL" not in os.environ:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "realestate-test-cache",
    }
}
