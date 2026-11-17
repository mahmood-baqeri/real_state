import os
import sys
from pathlib import Path
from typing import Any, Callable, Optional
from uuid import UUID
import django
from django.db import close_old_connections
from starlette.concurrency import run_in_threadpool
from .config import settings

_DJANGO_INITIALIZED = False


def init_django() -> None:
    global _DJANGO_INITIALIZED
    if _DJANGO_INITIALIZED:
        return
    backend_path = str(Path(settings.BACKEND_DIR).resolve())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        os.environ["DJANGO_SETTINGS_MODULE"] = (
            "config.settings.development"
            if os.environ.get("USE_LOCAL_SANDBOX_DB") == "1"
            else "config.settings.production"
        )
    django.setup()
    _DJANGO_INITIALIZED = True


async def run_django(
    fn: Callable[..., Any],
    *args: Any,
    agency_id: Optional[UUID] = None,
    **kwargs: Any,
) -> Any:
    """
    Executes synchronous Django ORM / domain service functions in FastAPI's worker
    threadpool while guaranteeing clean connection lifecycle and tenant context reset.
    """
    init_django()
    from common.tenant.context import set_current_agency_id

    def _wrapped():
        close_old_connections()
        set_current_agency_id(agency_id)
        try:
            return fn(*args, **kwargs)
        finally:
            set_current_agency_id(None)
            close_old_connections()

    return await run_in_threadpool(_wrapped)
