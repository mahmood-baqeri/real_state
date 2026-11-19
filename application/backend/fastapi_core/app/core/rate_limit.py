# Path: backend/fastapi_core/app/core/rate_limit.py

"""
Redis-based sliding-window rate limiter.

Usage:
    @router.post("/login")
    @rate_limit(scope="auth_login", limit=10, window_seconds=60)
    async def login(...): ...

Fail-open در صورت خطای Redis (تا در دسترس نبودن Redis، لاگین را قفل نکند).
"""
import functools
from typing import Callable, Optional

from fastapi import HTTPException, Request, status

from .config import settings

try:
    import redis as _redis_lib  # type: ignore
except ImportError:
    _redis_lib = None  # type: ignore

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_lib is None or not settings.RATE_LIMIT_ENABLED:
        return None
    if _redis_client is None:
        try:
            _redis_client = _redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception:
            return None
    return _redis_client


def _extract_request(args: tuple, kwargs: dict) -> Optional[Request]:
    for a in args:
        if isinstance(a, Request):
            return a
    req = kwargs.get("request")
    if isinstance(req, Request):
        return req
    return None


def rate_limit(*, scope: str, limit: int, window_seconds: int) -> Callable:
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            request = _extract_request(args, kwargs)
            ip = "unknown"
            if request is not None and request.client is not None:
                ip = request.client.host

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
                    # fail-open
                    pass

            return await fn(*args, **kwargs)

        return wrapper

    return decorator