# Path: backend/django_core/config/settings/production.py

from .base import *  # noqa: F401, F403

DEBUG = False

if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise RuntimeError("Production environment strictly requires PostgreSQL.")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
