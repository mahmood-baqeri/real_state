"""
Redis-based sliding-window rate limiter.
Usage: @rate_limit(scope="public_viewing", limit=10, window_seconds=60)
"""
import functools
from typing import Callable
from fastapi import HTTPException, Request, status

try:
    import redis  # type: ignore
except ImportError:
    redis = None  # type: ignore

from .config import settings

_redis_client = None


def _get_redis():
    global _redis_client
    if redis is None:
        return None
    if _redis_client is None:
        import os
        url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
        _redis_client = redis.from_url(url, decode_responses=True)
    return _redis_client


def rate_limit(*, scope: str, limit: int, window_seconds: int) -> Callable:
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            request: Request | None = None
            for a in args:
                if isinstance(a, Request):
                    request = a
                    break
            if request is None:
                request = kwargs.get("request")
            ip = request.client.host if request and request.client else "unknown"
            r = _get_redis()
            if r is not None:
                key = f"rl:{scope}:{ip}"
                try:
                    pipe = r.pipeline()
                    pipe.incr(key)
                    pipe.expire(key, window_seconds)
                    count, _ = pipe.execute()
                    if count and int(count) > limit:
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="تعداد درخواست‌های شما بیش از حد مجاز است. لطفاً کمی صبر کنید.",
                        )
                except HTTPException:
                    raise
                except Exception:
                    pass  # fail-open در صورت خطای Redis
            return await fn(*args, **kwargs)
        return wrapper
    return decorator