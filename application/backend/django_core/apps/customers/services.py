from typing import Optional
from uuid import UUID
from django.db import models, transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.agencies.models import AgencyAccessPolicy
from apps.appointments.models import ViewingAppointment
from apps.audit.services import record_audit_event
from apps.contracts.models import Contract
from apps.crm.models import CustomerInteractionLog, FollowUpTask
from apps.documents.models import Document
from apps.leads.models import Lead, LeadActivity
from apps.negotiations.models import Negotiation
from common.exceptions import (
    ConflictDomainError,
    NotFoundDomainError,
    PermissionDeniedDomainError,
    ValidationDomainError,
)
from common.permissions import (
    can_edit_customer,
    get_active_membership,
    get_agency_policy,
    has_agency_permission,
    is_super_admin,
)
from .models import Customer, CustomerRequirement, CustomerShare


def list_customers(
    *,
    user: User,
    agency_id: Optional[UUID],
    q: Optional[str] = None,
    customer_type: Optional[str] = None,
):
    qs = (
        Customer.objects.all_tenants()
        .filter(is_deleted=False)
        .select_related("assigned_membership__user", "agency")
        .prefetch_related("requirements", "shares__membership__user")
    )
    if agency_id:
        qs = qs.filter(agency_id=agency_id)
    elif not is_super_admin(user):
        raise PermissionDeniedDomainError("ابتدا آژانس را انتخاب کنید.")

    if not is_super_admin(user) and agency_id and not has_agency_permission(user, agency_id, "customer.view_all_agency"):
        membership = get_active_membership(user, agency_id)
        if not membership:
            return Customer.objects.none()
        policy = get_agency_policy(agency_id)
        if policy.customer_view_scope != AgencyAccessPolicy.CustomerViewScope.ALL_WITH_PERMISSION:
            qs = qs.filter(
                models.Q(assigned_membership=membership) | models.Q(shares__membership=membership)
            ).distinct()

    if customer_type:
        qs = qs.filter(customer_type=customer_type)
    if q:
        qs = qs.filter(
            models.Q(full_name__icontains=q)
            | models.Q(primary_phone__icontains=q)
            | models.Q(email__icontains=q)
        )
    return qs.order_by("-created_at")


def _resolve_customer(*, user: User, agency_id: Optional[UUID], customer_id: UUID) -> Customer:
    qs = list_customers(user=user, agency_id=agency_id).filter(id=customer_id)
    customer = qs.first()
    if not customer:
        raise NotFoundDomainError("مشتری یافت نشد.")
    return customer


def get_customer_detail(*, user: User, agency_id: Optional[UUID], customer_id: UUID) -> dict:
    customer = _resolve_customer(user=user, agency_id=agency_id, customer_id=customer_id)
    interactions = list(
        CustomerInteractionLog.objects.all_tenants()
        .filter(customer=customer)
        .select_related("membership__user", "created_by")
        .order_by("-created_at")[:50]
    )
    tasks = list(
        FollowUpTask.objects.all_tenants()
        .filter(customer=customer)
        .select_related("assigned_membership__user")
        .order_by("due_at")[:30]
    )
    contracts = list(
        Contract.objects.all_tenants()
        .filter(parties__customer=customer)
        .select_related("property", "deal_type")
        .distinct()
        .order_by("-created_at")[:20]
    )
    negotiations = list(
        Negotiation.objects.all_tenants()
        .filter(models.Q(customer=customer) | models.Q(owner_customer=customer))
        .select_related("property", "deal_type")
        .order_by("-created_at")[:20]
    )
    appointments = list(
        ViewingAppointment.objects.all_tenants()
        .filter(customer=customer)
        .select_related("property", "agent_membership__user")
        .order_by("-scheduled_start")[:20]
    )
    documents = list(
        Document.objects.all_tenants()
        .filter(customer=customer, is_deleted=False)
        .order_by("-created_at")[:20]
    )
    return {
        "customer": customer,
        "interactions": interactions,
        "tasks": tasks,
        "contracts": contracts,
        "negotiations": negotiations,
        "appointments": appointments,
        "documents": documents,
    }


@transaction.atomic
def create_customer(*, user: User, agency_id: Optional[UUID], data: dict) -> Customer:
    if not agency_id:
        raise ValidationDomainError("ابتدا آژانس فعال را انتخاب کنید.")
    membership = get_active_membership(user, agency_id)
    if not membership and not is_super_admin(user):
        raise PermissionDeniedDomainError("عضو فعال آژانس نیستید.")

    phone = data["primary_phone"].strip()
    if Customer.objects.all_tenants().filter(agency_id=agency_id, primary_phone=phone, is_deleted=False).exists():
        raise ConflictDomainError("مشتری با این شماره تماس قبلاً در آژانس ثبت شده است.")

    customer = Customer.objects.all_tenants().create(
        agency_id=agency_id,
        customer_type=data.get("customer_type", Customer.CustomerType.BUYER),
        full_name=data["full_name"].strip(),
        primary_phone=phone,
        secondary_phone=data.get("secondary_phone", ""),
        email=data.get("email", ""),
        source=data.get("source", "PORTAL"),
        assigned_membership_id=data.get("assigned_membership_id") or (membership.id if membership else None),
        lead_score=int(data.get("lead_score", 50)),
        readiness_level=data.get("readiness_level", "MEDIUM"),
        tags=data.get("tags", []),
        created_by=user,
    )
    record_audit_event(
        action="CUSTOMER_CREATED",
        resource_type="Customer",
        resource_id=str(customer.id),
        actor=user,
        agency_id=agency_id,
    )
    return customer


@transaction.atomic
def update_customer(*, user: User, agency_id: Optional[UUID], customer_id: UUID, data: dict) -> Customer:
    customer = _resolve_customer(user=user, agency_id=agency_id, customer_id=customer_id)
    if not can_edit_customer(user, customer):
        raise PermissionDeniedDomainError("عدم مجوز ویرایش اطلاعات مشتری.")
    for k in [
        "customer_type", "full_name", "primary_phone", "secondary_phone", "email",
        "source", "assigned_membership_id", "lead_score", "readiness_level", "tags", "is_active",
    ]:
        if k in data and data[k] is not None:
            setattr(customer, k, data[k])
    customer.updated_by = user
    customer.save()
    return customer


@transaction.atomic
def soft_delete_customer(*, user: User, agency_id: Optional[UUID], customer_id: UUID) -> Customer:
    customer = _resolve_customer(user=user, agency_id=agency_id, customer_id=customer_id)
    if not can_edit_customer(user, customer):
        raise PermissionDeniedDomainError("عدم مجوز بایگانی مشتری.")
    customer.is_deleted = True
    customer.is_active = False
    customer.deleted_at = timezone.now()
    customer.deleted_by = user
    customer.updated_by = user
    customer.save(update_fields=["is_deleted", "is_active", "deleted_at", "deleted_by", "updated_by", "updated_at"])
    record_audit_event(
        action="CUSTOMER_ARCHIVED",
        resource_type="Customer",
        resource_id=str(customer.id),
        actor=user,
        agency_id=customer.agency_id,
    )
    return customer


@transaction.atomic
def add_customer_interaction(
    *,
    user: User,
    agency_id: Optional[UUID],
    customer_id: UUID,
    channel: str = "NOTE",
    summary: str,
    is_private: bool = False,
) -> CustomerInteractionLog:
    customer = _resolve_customer(user=user, agency_id=agency_id, customer_id=customer_id)
    if not summary.strip():
        raise ValidationDomainError("متن تعامل الزامی است.")
    membership = get_active_membership(user, customer.agency_id)
    return CustomerInteractionLog.objects.all_tenants().create(
        agency_id=customer.agency_id,
        customer=customer,
        membership=membership,
        channel=channel or "NOTE",
        summary=summary.strip(),
        is_private=is_private,
        created_by=user,
    )


@transaction.atomic
def share_customer(
    *, user: User, agency_id: Optional[UUID], customer_id: UUID, target_membership_id: UUID, access_level: str = "VIEW"
) -> CustomerShare:
    customer = _resolve_customer(user=user, agency_id=agency_id, customer_id=customer_id)
    eff_agency_id = customer.agency_id
    if not (is_super_admin(user) or has_agency_permission(user, eff_agency_id, "customer.share") or can_edit_customer(user, customer)):
        raise PermissionDeniedDomainError("عدم مجوز اشتراک‌گذاری مشتری.")

    share, _ = CustomerShare.objects.update_or_create(
        customer=customer,
        membership_id=target_membership_id,
        defaults={"access_level": access_level, "created_by": user},
    )
    record_audit_event(
        action="CUSTOMER_SHARED",
        resource_type="Customer",
        resource_id=str(customer.id),
        actor=user,
        agency_id=eff_agency_id,
        after_state={"shared_with": str(target_membership_id), "access_level": access_level},
    )
    return share


@transaction.atomic
def add_customer_requirement(*, user: User, agency_id: Optional[UUID], customer_id: UUID, data: dict) -> CustomerRequirement:
    customer = _resolve_customer(user=user, agency_id=agency_id, customer_id=customer_id)
    return CustomerRequirement.objects.all_tenants().create(
        agency_id=customer.agency_id,
        customer=customer,
        deal_type_id=data["deal_type_id"],
        property_type_id=data["property_type_id"],
        target_city=data.get("target_city", ""),
        target_districts=data.get("target_districts", []),
        min_area_sqm=data.get("min_area_sqm", 0),
        max_area_sqm=data.get("max_area_sqm", 99999),
        currency_id=data.get("currency_id", "IRT"),
        min_budget=data.get("min_budget", 0),
        max_budget=data.get("max_budget", 0),
        min_bedrooms=int(data.get("min_bedrooms", 0)),
        priority=data.get("priority", "NORMAL"),
        created_by=user,
    )


def list_leads(
    *,
    user: User,
    agency_id: Optional[UUID],
    status_filter: Optional[str] = None,
    assigned_membership_id: Optional[UUID] = None,
    q: Optional[str] = None,
):
    qs = (
        Lead.objects.all_tenants()
        .filter(is_deleted=False)
        .select_related("property", "assigned_membership__user", "converted_customer", "agency")
        .prefetch_related("activities__created_by")
    )
    if agency_id:
        qs = qs.filter(agency_id=agency_id)
    elif not is_super_admin(user):
        raise PermissionDeniedDomainError("ابتدا آژانس را انتخاب کنید.")

    if not is_super_admin(user) and agency_id and not has_agency_permission(user, agency_id, "customer.view_all_agency"):
        membership = get_active_membership(user, agency_id)
        if not membership:
            return Lead.objects.none()
        qs = qs.filter(models.Q(assigned_membership=membership) | models.Q(assigned_membership__isnull=True))
    if status_filter:
        qs = qs.filter(status=status_filter)
    if assigned_membership_id:
        qs = qs.filter(assigned_membership_id=assigned_membership_id)
    if q:
        qs = qs.filter(models.Q(full_name__icontains=q) | models.Q(phone_number__icontains=q))
    return qs.order_by("-created_at")


def _resolve_lead(*, user: User, agency_id: Optional[UUID], lead_id: UUID) -> Lead:
    qs = list_leads(user=user, agency_id=agency_id).filter(id=lead_id)
    lead = qs.first()
    if not lead:
        raise NotFoundDomainError("سرنخ یافت نشد.")
    return lead


@transaction.atomic
def create_lead(*, user: Optional[User], agency_id: Optional[UUID], data: dict) -> Lead:
    if not agency_id:
        raise ValidationDomainError("ابتدا آژانس فعال را انتخاب کنید.")
    membership = get_active_membership(user, agency_id) if user else None
    if user and user.is_authenticated and not membership and not is_super_admin(user):
        raise PermissionDeniedDomainError("عضو فعال آژانس نیستید.")
    lead = Lead.objects.all_tenants().create(
        agency_id=agency_id,
        full_name=data["full_name"].strip(),
        phone_number=data["phone_number"].strip(),
        request_type=data.get("request_type", "BUY"),
        property_id=data.get("property_id"),
        source=data.get("source", "PORTAL"),
        assigned_membership_id=data.get("assigned_membership_id") or (membership.id if membership else None),
        notes=data.get("notes", ""),
        created_by=user if (user and user.is_authenticated) else None,
    )
    LeadActivity.objects.create(
        lead=lead,
        activity_type="CREATED",
        note=data.get("notes") or "ثبت سرنخ جدید در سیستم",
        created_by=user if (user and user.is_authenticated) else None,
    )
    return lead


@transaction.atomic
def update_lead(*, user: User, agency_id: Optional[UUID], lead_id: UUID, data: dict) -> Lead:
    lead = _resolve_lead(user=user, agency_id=agency_id, lead_id=lead_id)
    old_status = lead.status
    for k in [
        "full_name",
        "phone_number",
        "request_type",
        "property_id",
        "source",
        "assigned_membership_id",
        "status",
        "notes",
    ]:
        if k in data and data[k] is not None:
            val = data[k].strip() if isinstance(data[k], str) and k in ("full_name", "phone_number") else data[k]
            setattr(lead, k, val)
    lead.updated_by = user
    lead.save()
    if "status" in data and data["status"] and data["status"] != old_status:
        LeadActivity.objects.create(
            lead=lead,
            activity_type="STATUS_CHANGE",
            note=f"تغییر وضعیت از {old_status} به {lead.status}" + (f" — {data['notes']}" if data.get("notes") else ""),
            created_by=user,
        )
    return lead


@transaction.atomic
def update_lead_status(*, user: User, agency_id: Optional[UUID], lead_id: UUID, status_value: str, notes: Optional[str] = None) -> Lead:
    payload: dict = {"status": status_value}
    if notes is not None:
        payload["notes"] = notes
    return update_lead(user=user, agency_id=agency_id, lead_id=lead_id, data=payload)


@transaction.atomic
def add_lead_activity(
    *, user: User, agency_id: Optional[UUID], lead_id: UUID, activity_type: str = "NOTE", note: str
) -> LeadActivity:
    lead = _resolve_lead(user=user, agency_id=agency_id, lead_id=lead_id)
    if not note.strip():
        raise ValidationDomainError("متن یادداشت پیگیری الزامی است.")
    return LeadActivity.objects.create(
        lead=lead,
        activity_type=activity_type or "NOTE",
        note=note.strip(),
        created_by=user,
    )


@transaction.atomic
def soft_delete_lead(*, user: User, agency_id: Optional[UUID], lead_id: UUID) -> Lead:
    lead = _resolve_lead(user=user, agency_id=agency_id, lead_id=lead_id)
    lead.is_deleted = True
    lead.deleted_at = timezone.now()
    lead.deleted_by = user
    lead.updated_by = user
    lead.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_by", "updated_at"])
    record_audit_event(
        action="LEAD_ARCHIVED",
        resource_type="Lead",
        resource_id=str(lead.id),
        actor=user,
        agency_id=lead.agency_id,
    )
    return lead


@transaction.atomic
def convert_lead_to_customer(*, user: User, agency_id: Optional[UUID], lead_id: UUID) -> tuple[Lead, Customer]:
    lead = _resolve_lead(user=user, agency_id=agency_id, lead_id=lead_id)
    eff_agency_id = lead.agency_id
    membership = get_active_membership(user, eff_agency_id)
    customer, _ = Customer.objects.all_tenants().get_or_create(
        agency_id=eff_agency_id,
        primary_phone=lead.phone_number,
        defaults={
            "full_name": lead.full_name,
            "customer_type": Customer.CustomerType.TENANT if lead.request_type == "RENT" else Customer.CustomerType.BUYER,
            "source": lead.source,
            "assigned_membership": lead.assigned_membership or membership,
            "created_by": user,
        },
    )
    if customer.is_deleted:
        customer.is_deleted = False
        customer.is_active = True
        customer.save(update_fields=["is_deleted", "is_active", "updated_at"])
    lead.converted_customer = customer
    lead.status = Lead.Status.CONVERTED
    lead.updated_by = user
    lead.save(update_fields=["converted_customer", "status", "updated_by", "updated_at"])
    LeadActivity.objects.create(
        lead=lead,
        activity_type="CONVERTED",
        note=f"تبدیل به پرونده مشتری ({customer.full_name})",
        created_by=user,
    )
    record_audit_event(
        action="LEAD_CONVERTED",
        resource_type="Lead",
        resource_id=str(lead.id),
        actor=user,
        agency_id=eff_agency_id,
        after_state={"customer_id": str(customer.id)},
    )
    return lead, customer
