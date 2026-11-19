# Path: backend/django_core/apps/support/services.py

from datetime import timedelta
from typing import Optional
from uuid import UUID
from django.db import models, transaction
from django.db.models import Avg, Count
from django.utils import timezone
from apps.accounts.models import User
from apps.audit.services import record_audit_event
from common.exceptions import NotFoundDomainError, PermissionDeniedDomainError, ValidationDomainError
from common.permissions import get_active_membership, is_super_admin
from .models import (
    CannedReply,
    Ticket,
    TicketAttachment,
    TicketMessage,
    TicketStatusHistory,
)

PRIORITY_SLA_HOURS = {
    Ticket.Priority.URGENT: 4,
    Ticket.Priority.HIGH: 12,
    Ticket.Priority.NORMAL: 24,
    Ticket.Priority.LOW: 72,
}


def _is_support_staff(user: User, ticket: Ticket) -> bool:
    if is_super_admin(user):
        return True
    if ticket.agency_id:
        mem = get_active_membership(user, ticket.agency_id)
        if mem and mem.role.code in ("AGENCY_MANAGER", "BRANCH_MANAGER", "AGENCY_ACCOUNTANT"):
            return True
    return False


def list_tickets(*, user: User, agency_id: Optional[UUID], scope: Optional[str] = None, status_filter: Optional[str] = None):
    qs = Ticket.objects.select_related("agency", "created_by_user", "assigned_to_user").prefetch_related(
        "messages__sender", "messages__attachments", "status_history__changed_by"
    )
    if is_super_admin(user):
        if agency_id:
            qs = qs.filter(agency_id=agency_id)
    elif agency_id:
        mem = get_active_membership(user, agency_id)
        if mem and mem.role.code in ("AGENCY_MANAGER", "BRANCH_MANAGER", "AGENCY_ACCOUNTANT"):
            qs = qs.filter(models.Q(agency_id=agency_id) | models.Q(created_by_user=user))
        else:
            qs = qs.filter(models.Q(created_by_user=user) | models.Q(assigned_to_user=user))
    else:
        qs = qs.filter(models.Q(created_by_user=user) | models.Q(assigned_to_user=user))

    if scope:
        qs = qs.filter(scope=scope)
    if status_filter:
        qs = qs.filter(status=status_filter)
    return qs.order_by("-created_at")


def get_ticket(*, user: User, agency_id: Optional[UUID], ticket_id: UUID) -> tuple[Ticket, bool]:
    ticket = (
        Ticket.objects.select_related("agency", "created_by_user", "assigned_to_user")
        .prefetch_related("messages__sender", "messages__attachments", "status_history__changed_by")
        .filter(id=ticket_id)
        .first()
    )
    if not ticket:
        raise NotFoundDomainError("تیکت یافت نشد.")
    can_view_internal = _is_support_staff(user, ticket)
    if not (
        can_view_internal
        or ticket.created_by_user_id == user.id
        or ticket.assigned_to_user_id == user.id
    ):
        raise PermissionDeniedDomainError("اجازه مشاهده این تیکت را ندارید.")
    return ticket, can_view_internal


@transaction.atomic
def create_ticket(*, user: User, agency_id: Optional[UUID], data: dict) -> Ticket:
    scope = data.get("scope") or (Ticket.Scope.AGENCY if agency_id else Ticket.Scope.PLATFORM)
    if scope == Ticket.Scope.AGENCY and not agency_id:
        raise ValidationDomainError("برای تیکت داخلی آژانس باید آژانس فعال انتخاب شده باشد.")

    priority = data.get("priority", Ticket.Priority.NORMAL)
    sla_hours = PRIORITY_SLA_HOURS.get(priority, 24)
    ticket_number = f"TKT-{timezone.now().strftime('%y%m%d')}-{str(user.id)[:4].upper()}-{Ticket.objects.count() + 101}"

    ticket = Ticket.objects.create(
        ticket_number=ticket_number,
        scope=scope,
        agency_id=agency_id if scope == Ticket.Scope.AGENCY else data.get("agency_id"),
        created_by_user=user,
        category=data.get("category", Ticket.Category.GENERAL),
        priority=priority,
        status=Ticket.Status.OPEN,
        subject=data["subject"].strip(),
        sla_due_at=timezone.now() + timedelta(hours=sla_hours),
        created_by=user,
    )
    msg = TicketMessage.objects.create(
        ticket=ticket,
        sender=user,
        body=data["body"].strip(),
        is_internal_note=False,
        created_by=user,
    )
    for att in data.get("attachments", []):
        TicketAttachment.objects.create(
            message=msg,
            file_name=att["file_name"],
            file_url=att["file_url"],
            mime_type=att.get("mime_type", "application/octet-stream"),
            file_size_bytes=int(att.get("file_size_bytes", 0)),
        )
    TicketStatusHistory.objects.create(
        ticket=ticket,
        from_status="",
        to_status=Ticket.Status.OPEN,
        changed_by=user,
        note="ایجاد تیکت جدید",
    )
    record_audit_event(
        action="TICKET_CREATED",
        resource_type="Ticket",
        resource_id=str(ticket.id),
        actor=user,
        agency_id=ticket.agency_id,
    )
    return ticket


@transaction.atomic
def add_ticket_message(*, user: User, agency_id: Optional[UUID], ticket_id: UUID, data: dict) -> TicketMessage:
    ticket, can_view_internal = get_ticket(user=user, agency_id=agency_id, ticket_id=ticket_id)
    is_internal = bool(data.get("is_internal_note", False))
    if is_internal and not can_view_internal:
        raise PermissionDeniedDomainError("ثبت یادداشت داخلی فقط برای کارشناسان پشتیبانی مجاز است.")

    msg = TicketMessage.objects.create(
        ticket=ticket,
        sender=user,
        body=data["body"].strip(),
        is_internal_note=is_internal,
        created_by=user,
    )
    for att in data.get("attachments", []):
        TicketAttachment.objects.create(
            message=msg,
            file_name=att["file_name"],
            file_url=att["file_url"],
            mime_type=att.get("mime_type", "application/octet-stream"),
            file_size_bytes=int(att.get("file_size_bytes", 0)),
        )

    if not is_internal:
        prev = ticket.status
        next_status = (
            Ticket.Status.WAITING_USER
            if can_view_internal and ticket.created_by_user_id != user.id
            else Ticket.Status.IN_PROGRESS
        )
        if prev in (Ticket.Status.OPEN, Ticket.Status.WAITING_USER, Ticket.Status.RESOLVED):
            ticket.status = next_status
            ticket.save(update_fields=["status", "updated_at"])
            TicketStatusHistory.objects.create(
                ticket=ticket, from_status=prev, to_status=next_status, changed_by=user
            )
    return msg


@transaction.atomic
def update_ticket_status(
    *, user: User, agency_id: Optional[UUID], ticket_id: UUID, to_status: str, note: str = ""
) -> Ticket:
    ticket, is_staff = get_ticket(user=user, agency_id=agency_id, ticket_id=ticket_id)
    if not is_staff and not (ticket.created_by_user_id == user.id and to_status == Ticket.Status.CLOSED):
        raise PermissionDeniedDomainError("تغییر وضعیت تیکت فقط برای مسئول پشتیبانی مجاز است.")

    prev = ticket.status
    ticket.status = to_status
    if to_status == Ticket.Status.RESOLVED and not ticket.resolved_at:
        ticket.resolved_at = timezone.now()
    ticket.updated_by = user
    ticket.save(update_fields=["status", "resolved_at", "updated_by", "updated_at"])
    TicketStatusHistory.objects.create(
        ticket=ticket, from_status=prev, to_status=to_status, changed_by=user, note=note
    )
    return ticket


@transaction.atomic
def assign_ticket(*, user: User, agency_id: Optional[UUID], ticket_id: UUID, assignee_user_id: UUID) -> Ticket:
    ticket, is_staff = get_ticket(user=user, agency_id=agency_id, ticket_id=ticket_id)
    if not is_staff:
        raise PermissionDeniedDomainError("ارجاع تیکت فقط توسط مدیر یا پشتیبانی کل مجاز است.")
    assignee = User.objects.filter(id=assignee_user_id, status=User.Status.ACTIVE).first()
    if not assignee:
        raise NotFoundDomainError("کاربر مقصد یافت نشد.")
    ticket.assigned_to_user = assignee
    if ticket.status == Ticket.Status.OPEN:
        ticket.status = Ticket.Status.IN_PROGRESS
    ticket.save(update_fields=["assigned_to_user", "status", "updated_at"])
    return ticket


@transaction.atomic
def submit_ticket_rating(
    *, user: User, agency_id: Optional[UUID], ticket_id: UUID, rating: int, comment: str = ""
) -> Ticket:
    ticket, _ = get_ticket(user=user, agency_id=agency_id, ticket_id=ticket_id)
    if ticket.created_by_user_id != user.id and not is_super_admin(user):
        raise PermissionDeniedDomainError("فقط ثبت‌کننده تیکت می‌تواند امتیاز رضایت ثبت کند.")
    if rating < 1 or rating > 5:
        raise ValidationDomainError("امتیاز رضایت باید بین ۱ تا ۵ باشد.")
    ticket.satisfaction_rating = rating
    ticket.satisfaction_comment = comment.strip()
    ticket.save(update_fields=["satisfaction_rating", "satisfaction_comment", "updated_at"])
    return ticket


def list_canned_replies(*, user: User, agency_id: Optional[UUID]):
    qs = CannedReply.objects.filter(is_active=True)
    if agency_id:
        qs = qs.filter(models.Q(agency_id=agency_id) | models.Q(agency__isnull=True))
    else:
        qs = qs.filter(agency__isnull=True)
    return list(qs.order_by("title"))


@transaction.atomic
def create_canned_reply(*, user: User, agency_id: Optional[UUID], data: dict) -> CannedReply:
    if not is_super_admin(user):
        mem = get_active_membership(user, agency_id) if agency_id else None
        if not mem or mem.role.code != "AGENCY_MANAGER":
            raise PermissionDeniedDomainError("عدم مجوز ایجاد پاسخ آماده.")
    return CannedReply.objects.create(
        agency_id=agency_id,
        title=data["title"].strip(),
        category=data.get("category", Ticket.Category.GENERAL),
        body=data["body"].strip(),
        created_by=user,
    )


def get_ticket_report(*, user: User, agency_id: Optional[UUID]) -> dict:
    qs = list_tickets(user=user, agency_id=agency_id)
    by_status = list(qs.values("status").annotate(count=Count("id")))
    by_priority = list(qs.values("priority").annotate(count=Count("id")))
    avg_rating = qs.filter(satisfaction_rating__isnull=False).aggregate(a=Avg("satisfaction_rating"))["a"]
    return {
        "total": qs.count(),
        "by_status": by_status,
        "by_priority": by_priority,
        "avg_satisfaction": round(float(avg_rating), 2) if avg_rating is not None else None,
    }
