import os
from .base import *  # noqa: F401, F403

DEBUG = True

# PostgreSQL via DATABASE_URL is the primary database.
# Only fall back to local SQLite in isolated preview containers when USE_LOCAL_SANDBOX_DB=1.
if os.environ.get("USE_LOCAL_SANDBOX_DB") == "1" and os.environ.get("FORCE_POSTGRESQL") != "1":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "local_dev.sqlite3",
        }
    }

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "realestate-dev-cache",
    }
}
