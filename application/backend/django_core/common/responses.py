from typing import Any, Optional


def build_api_envelope(
    data: Any = None,
    *,
    success: bool = True,
    meta: Optional[dict[str, Any]] = None,
    errors: Optional[Any] = None,
) -> dict[str, Any]:
    return {
        "success": success,
        "data": data,
        "meta": meta or {},
        "errors": errors,
    }
