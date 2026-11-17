from typing import Any, Optional
from pydantic import BaseModel


class ApiEnvelope(BaseModel):
    success: bool = True
    data: Any = None
    meta: dict[str, Any] = {}
    errors: Optional[Any] = None


def ok(data: Any = None, *, meta: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    return {
        "success": True,
        "data": data,
        "meta": meta or {},
        "errors": None,
    }
