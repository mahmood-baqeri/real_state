# Path: backend/django_core/apps/appointments/services.py

from datetime import datetime
from typing import Optional
from uuid import UUID
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from apps.accounts.models import User
from apps.audit.services import record_audit_event
from apps.customers.models import Customer
from apps.properties.models import Property
from common.exceptions import ConflictDomainError, NotFoundDomainError, ValidationDomainError
from common.permissions import get_active_membership, has_agency_permission, is_super_admin
from common.tenant.context import tenant_bypass
from .models import ViewingAppointment


def list_appointments(*, user: User, agency_id: Optional[UUID]):
    if agency_id:
        qs = (
            ViewingAppointment.objects.all_tenants()
            .filter(agency_id=agency_id)
            .select_related("property", "customer", "agent_membership__user")
        )
        if is_super_admin(user) or has_agency_permission(user, agency_id, "appointment.view_all_agency"):
            return qs.order_by("-scheduled_start")
        membership = get_active_membership(user, agency_id)
        return qs.filter(agent_membership=membership).order_by("-scheduled_start") if membership else qs.none()

    with tenant_bypass():
        return (
            ViewingAppointment.objects.all_tenants()
            .filter(customer__user=user)
            .select_related("property", "customer", "agent_membership__user")
            .order_by("-scheduled_start")
        )


@transaction.atomic
def request_public_viewing(
    *, user: User, property_id: UUID, scheduled_start: datetime, scheduled_end: datetime, notes: str = ""
) -> ViewingAppointment:
    with tenant_bypass():
        prop = (
            Property.objects.all_tenants()
            .filter(id=property_id, status=Property.Status.PUBLISHED, is_deleted=False)
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
    prop = Property.objects.all_tenants().filter(id=property_id, agency_id=agency_id, is_deleted=False).first()
    if not prop:
        raise NotFoundDomainError("ملک یافت نشد.")
    customer = Customer.objects.all_tenants().filter(id=customer_id, agency_id=agency_id, is_deleted=False).first()
    if not customer:
        raise NotFoundDomainError("مشتری یافت نشد.")
    membership = get_active_membership(user, agency_id)
    target_agent_id = agent_membership_id or (membership.id if membership else None)
    if not target_agent_id:
        raise ValidationDomainError("مشاور بازدید مشخص نشده است.")

    try:
        if status_value in (ViewingAppointment.Status.CONFIRMED, ViewingAppointment.Status.RESCHEDULED):
            ViewingAppointment.check_conflict(
                agent_membership_id=target_agent_id,
                property_id=prop.id,
                start_at=scheduled_start,
                end_at=scheduled_end,
            )
        appt = ViewingAppointment.objects.all_tenants().create(
            agency_id=agency_id,
            property=prop,
            customer=customer,
            agent_membership_id=target_agent_id,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            status=status_value,
            created_by=user,
        )
    except DjangoValidationError as exc:
        raise ConflictDomainError(str(exc.message if hasattr(exc, "message") else exc))
    return appt


@transaction.atomic
def transition_appointment_status(
    *, user: User, agency_id: Optional[UUID], appt_id: UUID, new_status: str, agent_report: Optional[str] = None
) -> ViewingAppointment:
    appt = list_appointments(user=user, agency_id=agency_id).filter(id=appt_id).first()
    if not appt:
        raise NotFoundDomainError("قرار بازدید یافت نشد.")
    if new_status == ViewingAppointment.Status.CONFIRMED:
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
    appt.save()
    return appt
