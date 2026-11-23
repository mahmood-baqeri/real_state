import logging
import time
import uuid
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("bonyan.fastapi")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Attaches request correlation ID, timing telemetry header, security headers,
    and ensures unhandled internal exceptions never leak stack traces.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled API exception for %s %s (request_id=%s)", request.method, request.url.path, request_id)
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "data": None,
                    "meta": {"request_id": request_id},
                    "errors": [{"code": "INTERNAL_SERVER_ERROR", "detail": "خطای داخلی سرور رخ داد."}],
                    "detail": "خطای داخلی سرور رخ داد.",
                },
                headers={"X-Request-ID": request_id},
            )

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"
        if request.url.path.startswith("/api/v1/auth"):
            response.headers["Cache-Control"] = "no-store"
        return response
