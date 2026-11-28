from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Optional
import logging
from uuid import UUID

_current_agency_id: ContextVar[Optional[UUID]] = ContextVar("current_agency_id", default=None)
_bypass_tenant_filter: ContextVar[bool] = ContextVar("bypass_tenant_filter", default=False)

_ALLOWED_BYPASS_REASONS = {
    "authentication_attempt_log",
    "public_catalog",
    "public_viewing",
    "customer_portal",
    "platform_reports",
    "scoped_analytics",
    "operations_center",
    "scheduled_aggregation",
    "compliance_duplicate_detection",
    "platform_seed",
    "private_media_migration",
    "system_configuration",
    "system_notification",
    "notification_websocket_snapshot",
    "public_content",
    "public_complaint_tracking",
    "payment_callback",
    "data_migration",
    "demo_data_maintenance",
}


@contextmanager
def scoped_user(user_id: UUID) -> Iterator[None]:
    """شناسهٔ کاربر را برای سیاست‌های RLS در محدودهٔ عملیات تنظیم می‌کند."""
    from django.db import connection, transaction

    with transaction.atomic():
        previous = ""
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT COALESCE(current_setting('app.current_user_id', true), '')")
                previous = cursor.fetchone()[0]
                cursor.execute("SELECT set_config('app.current_user_id', %s, true)", [str(user_id)])
        try:
            yield
        finally:
            if connection.vendor == "postgresql" and not connection.needs_rollback:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT set_config('app.current_user_id', %s, true)", [previous])


def set_current_agency_id(agency_id: Optional[UUID]) -> None:
    _current_agency_id.set(agency_id)


def get_current_agency_id() -> Optional[UUID]:
    return _current_agency_id.get()


def is_tenant_bypassed() -> bool:
    return _bypass_tenant_filter.get()


@contextmanager
def tenant_bypass(*, reason: str) -> Iterator[None]:
    """Allowlisted internal cross-tenant execution; missing context is never an implicit bypass."""
    if reason not in _ALLOWED_BYPASS_REASONS:
        raise PermissionError("Tenant bypass reason is not allowlisted.")
    from django.db import connection, transaction
    token = _bypass_tenant_filter.set(True)
    try:
        with transaction.atomic():
            previous = ""
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COALESCE(current_setting('app.tenant_bypass', true), '')")
                    previous = cursor.fetchone()[0]
                    cursor.execute("SELECT set_config('app.tenant_bypass', 'on', true)")
            try:
                yield
            finally:
                if connection.vendor == "postgresql" and not connection.needs_rollback:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT set_config('app.tenant_bypass', %s, true)", [previous])
    finally:
        _bypass_tenant_filter.reset(token)


@contextmanager
def scoped_agency(agency_id: Optional[UUID]) -> Iterator[None]:
    """زمینهٔ آژانس را در پایتون و تراکنش PostgreSQL برای مدت عملیات تنظیم می‌کند."""
    from django.db import connection, transaction
    token = _current_agency_id.set(agency_id)
    try:
        with transaction.atomic():
            previous = ""
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COALESCE(current_setting('app.current_agency_id', true), '')")
                    previous = cursor.fetchone()[0]
                    cursor.execute(
                        "SELECT set_config('app.current_agency_id', %s, true)",
                        [str(agency_id) if agency_id else ""],
                    )
            try:
                yield
            finally:
                if connection.vendor == "postgresql" and not connection.needs_rollback:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT set_config('app.current_agency_id', %s, true)", [previous])
    finally:
        _current_agency_id.reset(token)
