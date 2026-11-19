# Path: backend/fastapi_core/middleware/__init__.py

"""FastAPI middleware package re-exports."""
from app.middleware.request_context import RequestContextMiddleware

__all__ = ["RequestContextMiddleware"]
