from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from django.utils import timezone
from apps.accounting.models import ChequeInstrument
from apps.accounts.models import User
from apps.audit.services import record_audit_event
from apps.contracts.models import Contract
from apps.crm.models import FollowUpTask
from apps.customers.models import Customer
from apps.properties.models import Property
from common.exceptions import ConflictDomainError, NotFoundDomainError, PermissionDeniedDomainError, ValidationDomainError
from common.permissions import can_edit_property, get_active_membership, has_agency_permission, is_super_admin
from common.tenant.context import tenant_bypass
from .models import ViewingAppointment


def list_appointments(*, user: User, agency_id: Optional[UUID]):
    if agency_id:
        qs = (
            ViewingAppointment.objects.all_tenants()
            .filter(agency_id=agency_id)
            .select_related("property", "customer", "agent_membership__user")
        )
        if is_super_admin(user):
            return qs.order_by("-scheduled_start")
        membership = get_active_membership(user, agency_id)
        if not membership:
            return qs.none()
        if membership.role.code == "BRANCH_MANAGER":
            return qs.filter(agent_membership__branch_id=membership.branch_id).order_by("-scheduled_start") if membership.branch_id else qs.none()
        if has_agency_permission(user, agency_id, "appointment.view_all_agency"):
            return qs.order_by("-scheduled_start")
        return qs.filter(agent_membership=membership).order_by("-scheduled_start")

    with tenant_bypass(reason="customer_portal"):
        return list(
            ViewingAppointment.objects.all_tenants()
            .filter(customer__user=user)
            .select_related("property", "customer", "agent_membership__user")
            .order_by("-scheduled_start")[:100]
        )


def get_unified_calendar(*, user: User, agency_id: Optional[UUID], days_ahead: int = 30) -> list[dict]:
    now = timezone.now()
    start_win = now - timedelta(days=14)
    end_win = now + timedelta(days=max(7, min(days_ahead, 120)))
    events: list[dict] = []

    appointment_source = list_appointments(user=user, agency_id=agency_id)
    if hasattr(appointment_source, "filter"):
        appts = list(appointment_source.filter(
            scheduled_start__gte=start_win, scheduled_start__lte=end_win
        ))
    else:
        appts = [
            item for item in appointment_source
            if start_win <= item.scheduled_start <= end_win
        ]
    for a in appts[:50]:
        events.append({
            "id": f"appt-{a.id}",
            "event_type": "VIEWING",
            "title": f"بازدید: {a.property.title}",
            "subtitle": f"مشتری: {a.customer.full_name} — مشاور: {a.agent_membership.user.full_name}",
            "start_at": a.scheduled_start.isoformat(),
            "end_at": a.scheduled_end.isoformat(),
            "status": a.status,
            "href": "/dashboard/appointments",
        })

    if agency_id:
        membership = get_active_membership(user, agency_id)
        task_qs = FollowUpTask.objects.all_tenants().filter(
            agency_id=agency_id, due_at__gte=start_win, due_at__lte=end_win
        ).select_related("customer", "assigned_membership__user")
        if not is_super_admin(user) and not has_agency_permission(user, agency_id, "customer.view_all_agency") and membership:
            task_qs = task_qs.filter(assigned_membership=membership)
        for t in task_qs[:40]:
            events.append({
                "id": f"task-{t.id}",
                "event_type": "TASK",
                "title": f"پیگیری: {t.title}",
                "subtitle": f"مشتری: {t.customer.full_name}",
                "start_at": t.due_at.isoformat(),
                "end_at": None,
                "status": t.status,
                "href": "/dashboard/crm",
            })

        if is_super_admin(user) or has_agency_permission(user, agency_id, "deal.view_all_agency"):
            for c in Contract.objects.all_tenants().filter(
                agency_id=agency_id, end_date__isnull=False, end_date__gte=start_win.date(), end_date__lte=end_win.date()
            ).select_related("property")[:30]:
                events.append({
                    "id": f"contract-{c.id}",
                    "event_type": "CONTRACT",
                    "title": f"پایان قرارداد: {c.contract_number}",
                    "subtitle": c.property.title if c.property else "",
                    "start_at": f"{c.end_date.isoformat()}T09:00:00Z",
                    "end_at": None,
                    "status": c.status,
                    "href": "/dashboard/contracts",
                })

        if is_super_admin(user) or has_agency_permission(user, agency_id, "accounting.view"):
            for ch in ChequeInstrument.objects.all_tenants().filter(
                agency_id=agency_id, due_date__gte=start_win, due_date__lte=end_win
            )[:30]:
                events.append({
                    "id": f"cheque-{ch.id}",
                    "event_type": "CHEQUE",
                    "title": f"سررسید چک {ch.cheque_number}",
                    "subtitle": f"مبلغ: {ch.amount} — {ch.direction}",
                    "start_at": ch.due_date.isoformat(),
                    "end_at": None,
                    "status": ch.status,
                    "href": "/dashboard/accounting",
                })

    events.sort(key=lambda e: e["start_at"])
    return events


@transaction.atomic
def request_public_viewing(
    *, user: User, property_id: UUID, scheduled_start: datetime, scheduled_end: datetime, notes: str = ""
) -> ViewingAppointment:
    with tenant_bypass(reason="public_viewing"): 
        prop = (
            Property.objects.all_tenants()
            .filter(
                id=property_id,
                status=Property.Status.PUBLISHED,
                visibility=Property.Visibility.PUBLIC_PORTAL,
                is_deleted=False,
            )
            .first()
        )
        if not prop:
            raise NotFoundDomainError("ملک مورد نظر یافت نشد.")
        assignment = prop.agent_assignments.first()
        if not assignment:
            raise ValidationDomainError("مشاور مسئول برای ملک ثبت نشده است.")

        customer, _ = Customer.objects.all_tenants().get_or_create(
            agency=prop.agency,
            primary_phone=user.phone_number,
            defaults={
                "user": user,
                "full_name": user.full_name,
                "customer_type": Customer.CustomerType.BUYER,
                "assigned_membership": assignment.membership,
                "created_by": user,
            },
        )
        try:
            appt = ViewingAppointment.schedule_safely(
                agency=prop.agency,
                property=prop,
                customer=customer,
                agent_membership=assignment.membership,
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end,
                status=ViewingAppointment.Status.REQUESTED,
                customer_feedback=notes,
                created_by=user,
            )
        except DjangoValidationError as exc:
            raise ConflictDomainError(str(exc.message if hasattr(exc, "message") else exc))

    record_audit_event(
        action="VIEWING_REQUESTED",
        resource_type="ViewingAppointment",
        resource_id=str(appt.id),
        actor=user,
        agency_id=prop.agency_id,
    )
    return appt


@transaction.atomic
def create_agency_appointment(
    *,
    user: User,
    agency_id: UUID,
    property_id: UUID,
    customer_id: UUID,
    scheduled_start: datetime,
    scheduled_end: datetime,
    agent_membership_id: Optional[UUID] = None,
    status_value: str = ViewingAppointment.Status.CONFIRMED,
) -> ViewingAppointment:
    prop = Property.objects.all_tenants().filter(
        id=property_id, agency_id=agency_id, is_deleted=False
    ).first()
    if not prop:
        raise NotFoundDomainError("ملک یافت نشد.")
    customer = Customer.objects.all_tenants().select_related("assigned_membership__branch").filter(
        id=customer_id, agency_id=agency_id, is_deleted=False
    ).first()
    if not customer:
        raise NotFoundDomainError("مشتری یافت نشد.")
    membership = get_active_membership(user, agency_id)
    if not membership and not is_super_admin(user):
        raise PermissionDeniedDomainError("عضو فعال آژانس نیستید.")
    if membership and not can_edit_property(user, prop):
        raise PermissionDeniedDomainError("برای ثبت بازدید این ملک مجوز ندارید.")
    if membership and membership.role.code == "BRANCH_MANAGER":
        if not membership.branch_id or not customer.assigned_membership_id or customer.assigned_membership.branch_id != membership.branch_id:
            raise PermissionDeniedDomainError("مشتری خارج از شعبه شماست.")
    elif membership and not has_agency_permission(user, agency_id, "customer.view_all_agency"):
        if customer.assigned_membership_id != membership.id and not customer.shares.filter(
            membership=membership, access_level="EDIT"
        ).filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())).exists():
            raise PermissionDeniedDomainError("دسترسی به این مشتری برای رزرو بازدید ندارید.")
    target_agent_id = agent_membership_id or (membership.id if membership else None)
    if not target_agent_id:
        raise ValidationDomainError("مشاور بازدید مشخص نشده است.")
    if status_value not in ViewingAppointment.Status.values:
        raise ValidationDomainError("وضعیت بازدید نامعتبر است.")

    from apps.accounts.models import AgencyMembership
    target_agent = AgencyMembership.objects.select_for_update().filter(
        id=target_agent_id, agency_id=agency_id, status=AgencyMembership.Status.ACTIVE
    ).first()
    if not target_agent:
        raise ValidationDomainError("مشاور انتخاب‌شده عضو فعال همین آژانس نیست.")
    if membership and membership.role.code == "BRANCH_MANAGER":
        if (
            not membership.branch_id
            or prop.branch_id != membership.branch_id
            or target_agent.branch_id != membership.branch_id
        ):
            raise PermissionDeniedDomainError("مدیر شعبه فقط می‌تواند بازدیدهای شعبه خودش را ثبت کند.")
    elif membership and target_agent.id != membership.id and not has_agency_permission(
        user, agency_id, "appointment.view_all_agency"
    ):
        raise PermissionDeniedDomainError("ثبت بازدید برای مشاور دیگر مجاز نیست.")

    try:
        appt = ViewingAppointment.schedule_safely(
            agency_id=agency_id,
            property=prop,
            customer=customer,
            agent_membership=target_agent,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            status=status_value,
            created_by=user,
        )
    except DjangoValidationError as exc:
        raise ConflictDomainError(str(exc.message if hasattr(exc, "message") else exc))
    record_audit_event(
        action="VIEWING_APPOINTMENT_CREATED",
        resource_type="ViewingAppointment",
        resource_id=str(appt.id),
        actor=user,
        agency_id=agency_id,
    )
    return appt


@transaction.atomic
def transition_appointment_status(
    *, user: User, agency_id: Optional[UUID], appt_id: UUID, new_status: str, agent_report: Optional[str] = None
) -> ViewingAppointment:
    """تغییر وضعیت بازدید را زیر قفل انجام می‌دهد و تکرار همان تغییر را می‌پذیرد."""
    visible = list_appointments(user=user, agency_id=agency_id).filter(id=appt_id).first()
    if not visible:
        raise NotFoundDomainError("قرار بازدید یافت نشد.")
    appt = ViewingAppointment.objects.all_tenants().select_for_update().filter(
        id=visible.id, agency_id=visible.agency_id
    ).first()
    if not appt:
        raise NotFoundDomainError("قرار بازدید یافت نشد.")
    if new_status not in ViewingAppointment.Status.values:
        raise ValidationDomainError("وضعیت بازدید نامعتبر است.")
    if new_status == appt.status and (agent_report is None or agent_report == appt.agent_report):
        return appt
    allowed = {
        ViewingAppointment.Status.REQUESTED: {
            ViewingAppointment.Status.CONFIRMED,
            ViewingAppointment.Status.REJECTED,
            ViewingAppointment.Status.CANCELLED,
        },
        ViewingAppointment.Status.CONFIRMED: {
            ViewingAppointment.Status.RESCHEDULED,
            ViewingAppointment.Status.COMPLETED,
            ViewingAppointment.Status.CANCELLED,
            ViewingAppointment.Status.NO_SHOW,
        },
        ViewingAppointment.Status.RESCHEDULED: {
            ViewingAppointment.Status.CONFIRMED,
            ViewingAppointment.Status.COMPLETED,
            ViewingAppointment.Status.CANCELLED,
            ViewingAppointment.Status.NO_SHOW,
        },
        ViewingAppointment.Status.COMPLETED: set(),
        ViewingAppointment.Status.CANCELLED: set(),
        ViewingAppointment.Status.REJECTED: set(),
        ViewingAppointment.Status.NO_SHOW: set(),
    }
    if new_status not in allowed.get(appt.status, set()):
        raise ConflictDomainError(f"انتقال وضعیت بازدید از {appt.status} به {new_status} مجاز نیست.")

    from apps.accounts.models import AgencyMembership
    locked_membership = AgencyMembership.objects.select_for_update().filter(
        id=appt.agent_membership_id, agency_id=appt.agency_id, status=AgencyMembership.Status.ACTIVE
    ).first()
    if not locked_membership:
        raise ConflictDomainError("مشاور بازدید دیگر عضو فعال این آژانس نیست.")
    Property.objects.select_for_update().filter(id=appt.property_id, agency_id=appt.agency_id).first()

    if new_status in (ViewingAppointment.Status.CONFIRMED, ViewingAppointment.Status.RESCHEDULED):
        try:
            ViewingAppointment.check_conflict(
                agent_membership_id=appt.agent_membership_id,
                property_id=appt.property_id,
                start_at=appt.scheduled_start,
                end_at=appt.scheduled_end,
                exclude_id=appt.id,
            )
        except DjangoValidationError as exc:
            raise ConflictDomainError(str(exc.message if hasattr(exc, "message") else exc))
    appt.status = new_status
    if agent_report is not None:
        appt.agent_report = agent_report
    appt.updated_by = user
    appt.save(update_fields=["status", "agent_report", "updated_by", "updated_at"])
    return appt
