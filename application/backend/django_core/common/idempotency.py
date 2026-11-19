# Path: backend/django_core/common/idempotency.py

from django.core.cache import cache


def check_and_store_idempotency_key(scope: str, key: str, ttl_seconds: int = 300) -> bool:
    """Returns True if key is fresh and claimed; False if duplicate request."""
    if not key:
        return True
    cache_key = f"idempotency:{scope}:{key}"
    return bool(cache.add(cache_key, "1", timeout=ttl_seconds))
