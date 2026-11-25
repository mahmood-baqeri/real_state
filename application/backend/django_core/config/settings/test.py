"""تنظیمات اختصاصی اجرای تست‌ها با اتصال کوتاه‌عمر و کش محلی."""

import os
from cryptography.fernet import Fernet
from .base import *  # noqa: F401, F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

if "TEST_DATABASE_URL" in os.environ:
    DATABASES = {"default": parse_database_url(os.environ["TEST_DATABASE_URL"])}
elif DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise RuntimeError("PostgreSQL is strictly required for test execution.")

DATABASES["default"]["CONN_MAX_AGE"] = 0
if not FIELD_ENCRYPTION_KEY:
    FIELD_ENCRYPTION_KEY = Fernet.generate_key().decode("ascii")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "realestate-test-cache",
    }
}
