from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Optional
from uuid import UUID

_current_agency_id: ContextVar[Optional[UUID]] = ContextVar("current_agency_id", default=None)
_bypass_tenant_filter: ContextVar[bool] = ContextVar("bypass_tenant_filter", default=False)


def set_current_agency_id(agency_id: Optional[UUID]) -> None:
    _current_agency_id.set(agency_id)


def get_current_agency_id() -> Optional[UUID]:
    return _current_agency_id.get()


def is_tenant_bypassed() -> bool:
    return _bypass_tenant_filter.get()


@contextmanager
def tenant_bypass() -> Iterator[None]:
    """Explicit context manager for SuperAdmin or Public Portal cross-tenant read queries."""
    token = _bypass_tenant_filter.set(True)
    try:
        yield
    finally:
        _bypass_tenant_filter.reset(token)


@contextmanager
def scoped_agency(agency_id: Optional[UUID]) -> Iterator[None]:
    """Explicitly bind execution to a given agency_id (useful in Celery tasks & tests)."""
    token = _current_agency_id.set(agency_id)
    try:
        yield
    finally:
        _current_agency_id.reset(token)
