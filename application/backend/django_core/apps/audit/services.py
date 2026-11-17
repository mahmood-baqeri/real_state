from typing import Any, Optional
from uuid import UUID
from apps.accounts.models import User
from common.exceptions import PermissionDeniedDomainError
from common.permissions import has_agency_permission, is_super_admin
from .models import AuditLog

from django.db import transaction


def record_audit_event(
    *,
    action: str,
    resource_type: str,
    resource_id: str = "",
    actor=None,
    agency_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: str = "",
    before_state: Optional[dict[str, Any]] = None,
    after_state: Optional[dict[str, Any]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> AuditLog | None:
    """
    ثبت audit log فقط پس از commit موفق تراکنش اصلی.
    اگر در محیط transaction نباشیم، مستقیم ثبت می‌شود.
    """
    def _create():
        return AuditLog.objects.create(
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id or ""),
            actor=actor if (actor and getattr(actor, "is_authenticated", False)) else None,
            agency_id=agency_id,
            ip_address=ip_address,
            user_agent=(user_agent or "")[:255],
            before_state=before_state,
            after_state=after_state,
            metadata=metadata or {},
        )

    if transaction.get_connection().in_atomic_block:
        transaction.on_commit(_create)
        return None
    return _create()


def list_audit_logs(
    *,
    user: User,
    agency_id: Optional[UUID],
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
):
    qs = AuditLog.objects.select_related("actor")
    if is_super_admin(user):
        if agency_id:
            qs = qs.filter(agency_id=agency_id)
    else:
        if not agency_id or not has_agency_permission(user, agency_id, "audit.view"):
            raise PermissionDeniedDomainError("عدم مجوز مشاهده لاگ ممیزی.")
        qs = qs.filter(agency_id=agency_id)
    if resource_type:
        qs = qs.filter(resource_type__icontains=resource_type)
    if action:
        qs = qs.filter(action__icontains=action)
    return qs.order_by("-created_at")
