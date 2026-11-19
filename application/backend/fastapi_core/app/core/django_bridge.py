# Path: backend/fastapi_core/app/core/django_bridge.py

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
    """
    Idempotent Django setup for FastAPI.
    - django_core/ را به sys.path اضافه می‌کند تا `config`, `apps`, `common` import شوند
    - DJANGO_SETTINGS_MODULE را قبل از django.setup() ست می‌کند
    """
    global _DJANGO_INITIALIZED
    if _DJANGO_INITIALIZED:
        return

    backend_path = str(Path(settings.BACKEND_DIR).resolve())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings.DJANGO_SETTINGS_MODULE)
    django.setup()
    _DJANGO_INITIALIZED = True


async def run_django(
    fn: Callable[..., Any],
    *args: Any,
    agency_id: Optional[UUID] = None,
    **kwargs: Any,
) -> Any:
    """
    اجرای sync Django code در threadpool امن.
    - connection lifecycle مدیریت می‌شود
    - tenant context ست/ریست می‌شود
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