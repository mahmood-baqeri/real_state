from typing import Optional
from uuid import UUID
from django.db import models, transaction
from apps.accounts.models import User
from apps.agencies.models import AgencyAccessPolicy
from apps.audit.services import record_audit_event
from apps.leads.models import Lead
from common.exceptions import ConflictDomainError, NotFoundDomainError, PermissionDeniedDomainError
from common.permissions import (
    can_edit_customer,
    get_active_membership,
    get_agency_policy,
    has_agency_permission,
    is_super_admin,
)
from .models import Customer, CustomerRequirement, CustomerShare


def list_customers(*, user: User, agency_id: UUID, q: Optional[str] = None, customer_type: Optional[str] = None):
    qs = (
        Customer.objects.all_tenants()
        .filter(agency_id=agency_id, is_deleted=False)
        .select_related("assigned_membership__user")
        .prefetch_related("requirements", "shares__membership__user")
    )
    if not is_super_admin(user) and not has_agency_permission(user, agency_id, "customer.view_all_agency"):
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


@transaction.atomic
def create_customer(*, user: User, agency_id: UUID, data: dict) -> Customer:
    membership = get_active_membership(user, agency_id)
    if not membership and not is_super_admin(user):
        raise PermissionDeniedDomainError("عضو فعال آژانس نیستید.")

    phone = data["primary_phone"].strip()
    if Customer.objects.all_tenants().filter(agency_id=agency_id, primary_phone=phone).exists():
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
def update_customer(*, user: User, agency_id: UUID, customer_id: UUID, data: dict) -> Customer:
    customer = list_customers(user=user, agency_id=agency_id).filter(id=customer_id).first()
    if not customer:
        raise NotFoundDomainError("مشتری یافت نشد.")
    if not can_edit_customer(user, customer):
        raise PermissionDeniedDomainError("عدم مجوز ویرایش اطلاعات مشتری.")
    for k in [
        "customer_type", "full_name", "secondary_phone", "email",
        "source", "assigned_membership_id", "lead_score", "readiness_level", "tags", "is_active",
    ]:
        if k in data and data[k] is not None:
            setattr(customer, k, data[k])
    customer.updated_by = user
    customer.save()
    return customer


@transaction.atomic
def share_customer(
    *, user: User, agency_id: UUID, customer_id: UUID, target_membership_id: UUID, access_level: str = "VIEW"
) -> CustomerShare:
    customer = list_customers(user=user, agency_id=agency_id).filter(id=customer_id).first()
    if not customer:
        raise NotFoundDomainError("مشتری یافت نشد.")
    if not (is_super_admin(user) or has_agency_permission(user, agency_id, "customer.share") or can_edit_customer(user, customer)):
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
        agency_id=agency_id,
        after_state={"shared_with": str(target_membership_id), "access_level": access_level},
    )
    return share


@transaction.atomic
def add_customer_requirement(*, user: User, agency_id: UUID, customer_id: UUID, data: dict) -> CustomerRequirement:
    customer = list_customers(user=user, agency_id=agency_id).filter(id=customer_id).first()
    if not customer:
        raise NotFoundDomainError("مشتری یافت نشد.")
    return CustomerRequirement.objects.all_tenants().create(
        agency_id=agency_id,
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


def list_leads(*, user: User, agency_id: UUID, status_filter: Optional[str] = None, q: Optional[str] = None):
    qs = (
        Lead.objects.all_tenants()
        .filter(agency_id=agency_id)
        .select_related("property", "assigned_membership__user", "converted_customer")
    )
    if not is_super_admin(user) and not has_agency_permission(user, agency_id, "customer.view_all_agency"):
        membership = get_active_membership(user, agency_id)
        if not membership:
            return Lead.objects.none()
        qs = qs.filter(models.Q(assigned_membership=membership) | models.Q(assigned_membership__isnull=True))
    if status_filter:
        qs = qs.filter(status=status_filter)
    if q:
        qs = qs.filter(models.Q(full_name__icontains=q) | models.Q(phone_number__icontains=q))
    return qs.order_by("-created_at")


@transaction.atomic
def create_lead(*, user: Optional[User], agency_id: UUID, data: dict) -> Lead:
    membership = get_active_membership(user, agency_id) if user else None
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
    return lead


@transaction.atomic
def update_lead_status(*, user: User, agency_id: UUID, lead_id: UUID, status_value: str, notes: Optional[str] = None) -> Lead:
    lead = Lead.objects.all_tenants().filter(id=lead_id, agency_id=agency_id).first()
    if not lead:
        raise NotFoundDomainError("سرنخ یافت نشد.")
    lead.status = status_value
    if notes is not None:
        lead.notes = notes
    lead.updated_by = user
    lead.save()
    return lead


@transaction.atomic
def convert_lead_to_customer(*, user: User, agency_id: UUID, lead_id: UUID) -> tuple[Lead, Customer]:
    lead = Lead.objects.all_tenants().filter(id=lead_id, agency_id=agency_id).first()
    if not lead:
        raise NotFoundDomainError("سرنخ یافت نشد.")
    membership = get_active_membership(user, agency_id)
    customer, _ = Customer.objects.all_tenants().get_or_create(
        agency_id=agency_id,
        primary_phone=lead.phone_number,
        defaults={
            "full_name": lead.full_name,
            "customer_type": Customer.CustomerType.TENANT if lead.request_type == "RENT" else Customer.CustomerType.BUYER,
            "source": lead.source,
            "assigned_membership": lead.assigned_membership or membership,
            "created_by": user,
        },
    )
    lead.converted_customer = customer
    lead.status = Lead.Status.CONVERTED
    lead.updated_by = user
    lead.save(update_fields=["converted_customer", "status", "updated_by", "updated_at"])
    record_audit_event(
        action="LEAD_CONVERTED",
        resource_type="Lead",
        resource_id=str(lead.id),
        actor=user,
        agency_id=agency_id,
        after_state={"customer_id": str(customer.id)},
    )
    return lead, customer
