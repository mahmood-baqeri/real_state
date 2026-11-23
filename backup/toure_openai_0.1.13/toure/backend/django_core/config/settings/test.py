import os
from .base import *  # noqa: F401, F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

if "TEST_DATABASE_URL" in os.environ:
    DATABASES = {"default": parse_database_url(os.environ["TEST_DATABASE_URL"])}
elif DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise RuntimeError("PostgreSQL is strictly required for test execution.")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "realestate-test-cache",
    }
}
