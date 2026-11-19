# Path: backend/fastapi_core/dependencies/__init__.py

"""FastAPI dependencies package re-exports."""
from app.dependencies.auth import get_current_user, get_optional_user, resolve_agency_context

__all__ = ["get_current_user", "get_optional_user", "resolve_agency_context"]
