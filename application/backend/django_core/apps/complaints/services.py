# Path: backend/django_core/apps/complaints/services.py

from typing import Optional
from uuid import UUID
from django.db import models, transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.audit.services import record_audit_event
from common.exceptions import NotFoundDomainError, PermissionDeniedDomainError, ValidationDomainError
from common.permissions import get_active_membership, is_super_admin
from .models import Complaint, ComplaintNote


def _normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if digits.startswith("98") and len(digits) == 12:
        return "0" + digits[2:]
    return digits


def _can_manage_complaint(user: User, complaint: Complaint) -> bool:
    if is_super_admin(user):
        return True
    if complaint.assigned_to_user_id == user.id:
        return True
    if complaint.agency_id and not complaint.is_confidential:
        mem = get_active_membership(user, complaint.agency_id)
        if mem and mem.role.code in ("AGENCY_MANAGER", "BRANCH_MANAGER"):
            return True
    return False


def list_complaints(*, user: User, agency_id: Optional[UUID], status_filter: Optional[str] = None):
    qs = Complaint.objects.select_related("agency", "complainant_user", "assigned_to_user").prefetch_related(
        "notes__author"
    )
    if is_super_admin(user):
        if agency_id:
            qs = qs.filter(agency_id=agency_id)
    elif agency_id:
        mem = get_active_membership(user, agency_id)
        if mem and mem.role.code in ("AGENCY_MANAGER", "BRANCH_MANAGER"):
            qs = qs.filter(
                models.Q(agency_id=agency_id, is_confidential=False)
                | models.Q(assigned_to_user=user)
                | models.Q(complainant_user=user)
            )
        else:
            qs = qs.filter(models.Q(complainant_user=user) | models.Q(assigned_to_user=user))
    else:
        qs = qs.filter(models.Q(complainant_user=user) | models.Q(assigned_to_user=user))

    if status_filter:
        qs = qs.filter(status=status_filter)
    return qs.order_by("-created_at")


@transaction.atomic
def create_complaint(*, user: Optional[User], agency_id: Optional[UUID], data: dict) -> Complaint:
    phone = _normalize_phone(data.get("complainant_phone") or (user.phone_number if user else ""))
    if len(phone) < 8:
        raise ValidationDomainError("شماره تماس معتبر برای رهگیری شکایت الزامی است.")

    seq = Complaint.objects.count() + 1001
    tracking_code = f"CMP-{timezone.now().strftime('%y%m')}-{seq}"

    complaint = Complaint.objects.create(
        tracking_code=tracking_code,
        complainant_user=user,
        complainant_name=(data.get("complainant_name") or (user.full_name if user else "ناشناس")).strip(),
        complainant_phone=phone,
        agency_id=data.get("agency_id") or agency_id,
        target_type=data.get("target_type", Complaint.TargetType.AGENCY),
        target_title=data.get("target_title", "").strip(),
        subject=data["subject"].strip(),
        description=data["description"].strip(),
        is_confidential=bool(data.get("is_confidential", True)),
        status=Complaint.Status.OPEN,
        created_by=user,
    )
    record_audit_event(
        action="COMPLAINT_FILED",
        resource_type="Complaint",
        resource_id=str(complaint.id),
        actor=user,
        agency_id=complaint.agency_id,
    )
    return complaint


def track_public_complaint(*, tracking_code: str, phone_number: str) -> dict:
    norm_phone = _normalize_phone(phone_number)
    complaint = Complaint.objects.filter(tracking_code=tracking_code.strip().upper()).first()
    if not complaint or complaint.complainant_phone != norm_phone:
        raise NotFoundDomainError("شکایتی با این کد رهگیری و شماره تماس یافت نشد.")
    return {
        "tracking_code": complaint.tracking_code,
        "subject": complaint.subject,
        "target_type": complaint.target_type,
        "status": complaint.status,
        "resolution_summary": complaint.resolution_summary,
        "created_at": complaint.created_at.isoformat(),
        "resolved_at": complaint.resolved_at.isoformat() if complaint.resolved_at else None,
    }


@transaction.atomic
def add_complaint_note(*, user: User, complaint_id: UUID, note: str, is_confidential: bool = True) -> ComplaintNote:
    complaint = Complaint.objects.filter(id=complaint_id).first()
    if not complaint:
        raise NotFoundDomainError("شکایت یافت نشد.")
    if not _can_manage_complaint(user, complaint):
        raise PermissionDeniedDomainError("دسترسی برای ثبت یادداشت رسیدگی روی این شکایت ندارید.")
    return ComplaintNote.objects.create(
        complaint=complaint,
        author=user,
        note=note.strip(),
        is_confidential=is_confidential,
        created_by=user,
    )


@transaction.atomic
def update_complaint_status(
    *,
    user: User,
    complaint_id: UUID,
    to_status: str,
    resolution_summary: Optional[str] = None,
    assigned_to_user_id: Optional[UUID] = None,
) -> Complaint:
    complaint = Complaint.objects.filter(id=complaint_id).first()
    if not complaint:
        raise NotFoundDomainError("شکایت یافت نشد.")
    if not _can_manage_complaint(user, complaint):
        raise PermissionDeniedDomainError("اجازه تغییر وضعیت یا ارجاع این شکایت را ندارید.")

    complaint.status = to_status
    if resolution_summary is not None:
        complaint.resolution_summary = resolution_summary.strip()
    if assigned_to_user_id is not None:
        assignee = User.objects.filter(id=assigned_to_user_id, status=User.Status.ACTIVE).first()
        if not assignee:
            raise NotFoundDomainError("کاربر مسئول یافت نشد.")
        complaint.assigned_to_user = assignee
    if to_status == Complaint.Status.RESOLVED and not complaint.resolved_at:
        complaint.resolved_at = timezone.now()
    complaint.updated_by = user
    complaint.save()

    record_audit_event(
        action=f"COMPLAINT_STATUS_{to_status}",
        resource_type="Complaint",
        resource_id=str(complaint.id),
        actor=user,
        agency_id=complaint.agency_id,
    )
    return complaint
