"""اتصال درخواست‌های FastAPI به سرویس‌های همگام Django."""

import os
import sys
from hmac import compare_digest
from pathlib import Path
from typing import Any, Callable, Optional
from uuid import UUID
import django
from django.db import close_old_connections
from starlette.concurrency import run_in_threadpool
from .config import settings

_DJANGO_INITIALIZED = False


def init_django() -> None:
    """تنظیمات Django را برای استفاده از مدل‌ها و سرویس‌ها بارگذاری می‌کند."""
    global _DJANGO_INITIALIZED
    if _DJANGO_INITIALIZED:
        return
    backend_path = str(Path(settings.BACKEND_DIR).resolve())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        os.environ["DJANGO_SETTINGS_MODULE"] = (
            "config.settings.production"
            if os.environ.get("DJANGO_ENV") == "production"
            else "config.settings.development"
        )
    django.setup()
    from django.conf import settings as django_settings

    if os.environ.get("DJANGO_SETTINGS_MODULE") == "config.settings.production" and not compare_digest(
        settings.JWT_SIGNING_KEY.encode(), django_settings.JWT_SIGNING_KEY.encode()
    ):
        raise RuntimeError("FastAPI and Django must use the same validated JWT signing key.")
    _DJANGO_INITIALIZED = True


async def run_django(
    fn: Callable[..., Any],
    *args: Any,
    agency_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    **kwargs: Any,
) -> Any:
    """سرویس همگام را در ترد جدا و با زمینهٔ تراکنشی آژانس اجرا می‌کند."""
    init_django()
    from common.tenant.context import set_current_agency_id

    def _wrapped():
        """زمینهٔ درخواست را روی اتصال پایگاه داده برقرار و سپس پاک می‌کند."""
        close_old_connections()
        set_current_agency_id(agency_id)
        from django.db import connection, transaction
        try:
            with transaction.atomic():
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT set_config('app.current_agency_id', %s, true), "
                            "set_config('app.current_user_id', %s, true)",
                            [str(agency_id) if agency_id else "", str(user_id) if user_id else ""],
                        )
                return fn(*args, **kwargs)
        finally:
            set_current_agency_id(None)
            close_old_connections()

    return await run_in_threadpool(_wrapped)
