# Path: backend/fastapi_core/services/__init__.py

"""FastAPI orchestration services package re-exports."""
from app.services.matching_service import score_property_for_requirement

__all__ = ["score_property_for_requirement"]
