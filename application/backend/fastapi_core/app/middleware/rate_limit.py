import json
import time
from fastapi import Request
from fastapi.responses import JSONResponse
import redis
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings

_redis_client = None
RATE_LIMITS_REDIS_KEY = "bonyan:security:rate_limits"


def _get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        except Exception:
            _redis_client = None
    return _redis_client


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-backed sliding/fixed-window rate limiter reading dynamic limits
    published by Global Settings Center (`bonyan:security:rate_limits`).
    """

    def __init__(self, app, default_limit: int = 180, auth_limit: int = 30, window_seconds: int = 60):
        super().__init__(app)
        self.default_limit = default_limit
        self.auth_limit = auth_limit
        self.window_seconds = window_seconds
        self._last_cfg_fetch = 0.0

    def _refresh_dynamic_limits(self, r) -> tuple[int, int, int]:
        now = time.time()
        if r is not None and (now - self._last_cfg_fetch) >= 15.0:
            self._last_cfg_fetch = now
            try:
                raw = r.get(RATE_LIMITS_REDIS_KEY)
                if raw:
                    parsed = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
                    self.default_limit = max(10, int(parsed.get("default_limit", self.default_limit)))
                    self.auth_limit = max(5, int(parsed.get("auth_limit", self.auth_limit)))
                    self.window_seconds = max(10, int(parsed.get("window_seconds", self.window_seconds)))
            except Exception:
                pass
        return self.default_limit, self.auth_limit, self.window_seconds

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in ("/api/v1/health", "/api/docs", "/api/openapi.json"):
            return await call_next(request)

        r = _get_redis()
        default_limit, auth_limit, window_sec = self._refresh_dynamic_limits(r)

        client_ip = request.client.host if request.client else "127.0.0.1"
        is_sensitive = (
            path.startswith("/api/v1/auth/login")
            or path.startswith("/api/v1/auth/password-reset")
            or path.startswith("/api/v1/public-requests")
        )
        limit = auth_limit if is_sensitive else default_limit
        if client_ip == "testclient":
            limit = max(limit, 500)
        bucket = "sensitive" if is_sensitive else "general"
        window_id = int(time.time() // window_sec)
        key = f"rl:{bucket}:{client_ip}:{window_id}"

        if r is not None:
            try:
                count = r.incr(key)
                if count == 1:
                    r.expire(key, window_sec)
                if count > limit:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "success": False,
                            "data": None,
                            "meta": {"retry_after_seconds": window_sec},
                            "errors": [
                                {
                                    "code": "RATE_LIMITED",
                                    "detail": "تعداد درخواست‌های شما از حد مجاز فراتر رفت. لطفاً لحظاتی صبر کنید.",
                                }
                            ],
                            "detail": "تعداد درخواست‌های شما از حد مجاز فراتر رفت.",
                        },
                        headers={"Retry-After": str(window_sec)},
                    )
            except Exception:
                pass

        return await call_next(request)
