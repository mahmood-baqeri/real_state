from typing import Optional
from difflib import SequenceMatcher
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
    if not agency_id:
        return Customer.objects.none()
    qs = qs.filter(agency_id=agency_id)
    if not is_super_admin(user):
        membership = get_active_membership(user, agency_id)
        if not membership:
            return Customer.objects.none()
        if membership.role.code == "BRANCH_MANAGER":
            if not membership.branch_id:
                return Customer.objects.none()
            qs = qs.filter(assigned_membership__branch_id=membership.branch_id)
        elif not has_agency_permission(user, agency_id, "customer.view_all_agency"):
            # ALL_WITH_PERMISSION means explicit permission is mandatory; it must
            # never turn into an implicit all-customer grant when permission is absent.
            qs = qs.filter(
                models.Q(assigned_membership=membership)
                | models.Q(shares__membership=membership, shares__expires_at__isnull=True)
                | models.Q(shares__membership=membership, shares__expires_at__gt=timezone.now())
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
    membership = get_active_membership(user, customer.agency_id)

    interaction_qs = CustomerInteractionLog.objects.all_tenants().filter(customer=customer)
    if not has_agency_permission(user, customer.agency_id, "crm.private_note.view"):
        interaction_qs = interaction_qs.filter(
            models.Q(is_private=False) | models.Q(created_by=user) | models.Q(membership=membership)
        )
    interactions = list(
        interaction_qs.select_related("membership__user", "created_by").order_by("-created_at")[:50]
    )

    can_view_related = has_agency_permission(user, customer.agency_id, "customer.related_records.view")
    task_qs = FollowUpTask.objects.all_tenants().filter(customer=customer)
    contract_qs = Contract.objects.all_tenants().filter(parties__customer=customer)
    negotiation_qs = Negotiation.objects.all_tenants().filter(
        models.Q(customer=customer) | models.Q(owner_customer=customer)
    )
    appointment_qs = ViewingAppointment.objects.all_tenants().filter(customer=customer)

    if membership and membership.role.code == "BRANCH_MANAGER":
        if not membership.branch_id:
            raise PermissionDeniedDomainError("مدیر شعبه فاقد شعبه فعال است.")
        task_qs = task_qs.filter(assigned_membership__branch_id=membership.branch_id)
        contract_qs = contract_qs.filter(property__branch_id=membership.branch_id)
        negotiation_qs = negotiation_qs.filter(property__branch_id=membership.branch_id)
        appointment_qs = appointment_qs.filter(agent_membership__branch_id=membership.branch_id)
    elif not can_view_related:
        if not membership:
            task_qs = task_qs.none()
            contract_qs = contract_qs.none()
            negotiation_qs = negotiation_qs.none()
            appointment_qs = appointment_qs.none()
        else:
            task_qs = task_qs.filter(models.Q(assigned_membership=membership) | models.Q(created_by=user))
            contract_qs = contract_qs.filter(
                models.Q(property__agent_assignments__membership=membership) | models.Q(created_by=user)
            ).distinct()
            negotiation_qs = negotiation_qs.filter(
                models.Q(agent_membership=membership) | models.Q(created_by=user)
            )
            appointment_qs = appointment_qs.filter(agent_membership=membership)

    tasks = list(task_qs.select_related("assigned_membership__user").order_by("due_at")[:30])
    contracts = list(
        contract_qs.select_related("property", "deal_type").distinct().order_by("-created_at")[:20]
    )
    negotiations = list(
        negotiation_qs.select_related("property", "deal_type").order_by("-created_at")[:20]
    )
    appointments = list(
        appointment_qs.select_related("property", "agent_membership__user").order_by("-scheduled_start")[:20]
    )

    documents = []
    if membership and has_agency_permission(user, customer.agency_id, "document.view"):
        document_qs = Document.objects.all_tenants().filter(customer=customer, agency_id=customer.agency_id, is_deleted=False)
        if not has_agency_permission(user, customer.agency_id, "document.manage_access"):
            document_qs = document_qs.exclude(access_level=Document.AccessLevel.CONFIDENTIAL)
        if membership.role.code == "BRANCH_MANAGER":
            document_qs = document_qs.filter(
                models.Q(property__branch_id=membership.branch_id)
                | models.Q(customer__assigned_membership__branch_id=membership.branch_id)
                | models.Q(contract__property__branch_id=membership.branch_id)
            )
        elif not has_agency_permission(user, customer.agency_id, "customer.related_records.view"):
            document_qs = document_qs.filter(
                models.Q(created_by=user)
                | models.Q(property__agent_assignments__membership=membership)
                | models.Q(customer__assigned_membership=membership)
                | models.Q(contract__property__agent_assignments__membership=membership)
                | models.Q(contract__parties__customer__assigned_membership=membership)
            ).distinct()
        documents = list(document_qs.order_by("-created_at")[:20])

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
    if not (is_super_admin(user) or has_agency_permission(user, agency_id, "customer.create")):
        raise PermissionDeniedDomainError("مجوز ایجاد پرونده مشتری را ندارید.")

    requested_assignee = data.get("assigned_membership_id")
    if membership and membership.role.code == "BRANCH_MANAGER":
        if not membership.branch_id:
            raise PermissionDeniedDomainError("مدیر شعبه باید به یک شعبه مشخص متصل باشد.")
        assigned_id = requested_assignee or membership.id
    elif is_super_admin(user) or has_agency_permission(user, agency_id, "customer.edit_all_agency"):
        assigned_id = requested_assignee or (membership.id if membership else None)
    else:
        assigned_id = membership.id if membership else None
    if assigned_id:
        from apps.accounts.models import AgencyMembership
        target = AgencyMembership.objects.filter(
            id=assigned_id, agency_id=agency_id, status=AgencyMembership.Status.ACTIVE
        ).first()
        if not target:
            raise ValidationDomainError("مشاور تخصیص‌یافته عضو فعال همین آژانس نیست.")
        if membership and membership.role.code == "BRANCH_MANAGER" and target.branch_id != membership.branch_id:
            raise PermissionDeniedDomainError("مدیر شعبه فقط می‌تواند مشتری را به مشاور همان شعبه تخصیص دهد.")

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
        assigned_membership_id=assigned_id,
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
    if data.get("assigned_membership_id"):
        from apps.accounts.models import AgencyMembership
        target = AgencyMembership.objects.filter(
            id=data["assigned_membership_id"], agency_id=customer.agency_id,
            status=AgencyMembership.Status.ACTIVE
        ).first()
        if not target:
            raise ValidationDomainError("مشاور تخصیص‌یافته عضو فعال همین آژانس نیست.")
        current = get_active_membership(user, customer.agency_id)
        if current and current.role.code == "BRANCH_MANAGER":
            if not current.branch_id or target.branch_id != current.branch_id:
                raise PermissionDeniedDomainError("مدیر شعبه فقط می‌تواند مشتری را به مشاور همان شعبه تخصیص دهد.")
        elif current and not (
            is_super_admin(user) or has_agency_permission(user, customer.agency_id, "customer.edit_all_agency")
        ) and target.id != current.id:
            raise PermissionDeniedDomainError("تغییر مشاور تخصیص‌یافته مجاز نیست.")
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
    *, user: User, agency_id: Optional[UUID], customer_id: UUID, target_membership_id: UUID,
    access_level: str = "VIEW", expires_at=None
) -> CustomerShare:
    customer = _resolve_customer(user=user, agency_id=agency_id, customer_id=customer_id)
    eff_agency_id = customer.agency_id
    if not (is_super_admin(user) or has_agency_permission(user, eff_agency_id, "customer.share")):
        raise PermissionDeniedDomainError("مجوز مستقل اشتراک‌گذاری مشتری را ندارید.")
    if access_level not in CustomerShare.AccessLevel.values:
        raise ValidationDomainError("سطح دسترسی اشتراک مشتری نامعتبر است.")
    if expires_at and expires_at <= timezone.now():
        raise ValidationDomainError("زمان انقضای اشتراک باید در آینده باشد.")
    from apps.accounts.models import AgencyMembership
    target = AgencyMembership.objects.filter(
        id=target_membership_id, agency_id=eff_agency_id, status=AgencyMembership.Status.ACTIVE
    ).first()
    if not target:
        raise ValidationDomainError("عضو مقصد باید عضو فعال همین آژانس باشد.")
    sharer_membership = get_active_membership(user, eff_agency_id)
    if sharer_membership and sharer_membership.role.code == "BRANCH_MANAGER":
        if not sharer_membership.branch_id or target.branch_id != sharer_membership.branch_id:
            raise PermissionDeniedDomainError("مدیر شعبه فقط می‌تواند مشتری را با اعضای شعبه خود به اشتراک بگذارد.")

    share, _ = CustomerShare.objects.update_or_create(
        customer=customer,
        membership_id=target_membership_id,
        defaults={"access_level": access_level, "expires_at": expires_at, "created_by": user},
    )
    record_audit_event(
        action="CUSTOMER_SHARED",
        resource_type="Customer",
        resource_id=str(customer.id),
        actor=user,
        agency_id=eff_agency_id,
        after_state={"shared_with": str(target_membership_id), "access_level": access_level, "expires_at": expires_at.isoformat() if expires_at else None},
    )
    return share


@transaction.atomic
def revoke_customer_share(*, user: User, agency_id: Optional[UUID], customer_id: UUID, membership_id: UUID) -> bool:
    customer = _resolve_customer(user=user, agency_id=agency_id, customer_id=customer_id)
    if not (is_super_admin(user) or has_agency_permission(user, customer.agency_id, "customer.share")):
        raise PermissionDeniedDomainError("مجوز مدیریت اشتراک مشتری را ندارید.")
    share = CustomerShare.objects.filter(customer=customer, membership_id=membership_id).first()
    if not share:
        raise NotFoundDomainError("اشتراک مشتری یافت نشد.")
    share.delete()
    record_audit_event(action="CUSTOMER_SHARE_REVOKED", resource_type="Customer", resource_id=str(customer.pk), actor=user, agency_id=customer.agency_id, after_state={"membership_id": str(membership_id)})
    return True


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

    if not is_super_admin(user) and agency_id:
        membership = get_active_membership(user, agency_id)
        if not membership:
            return Lead.objects.none()
        if membership.role.code == "BRANCH_MANAGER":
            if not membership.branch_id:
                return Lead.objects.none()
            qs = qs.filter(assigned_membership__branch_id=membership.branch_id)
        elif not has_agency_permission(user, agency_id, "customer.view_all_agency"):
            qs = qs.filter(assigned_membership=membership)
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
    from apps.accounts.models import AgencyMembership
    from apps.properties.models import Property, PropertyAgentAssignment
    property_id = data.get("property_id")
    linked_property = None
    if property_id:
        linked_property = Property.objects.all_tenants().filter(
            id=property_id, agency_id=agency_id, is_deleted=False
        ).first()
        if not linked_property:
            raise ValidationDomainError("ملک مرتبط با سرنخ متعلق به این آژانس نیست.")
    requested_assignee = data.get("assigned_membership_id")
    if membership and membership.role.code == "BRANCH_MANAGER":
        if not membership.branch_id or (linked_property and linked_property.branch_id != membership.branch_id):
            raise PermissionDeniedDomainError("مدیر شعبه فقط می‌تواند برای ملک شعبه خودش سرنخ ثبت کند.")
        assigned_id = membership.id
    elif membership and (is_super_admin(user) or has_agency_permission(user, agency_id, "customer.view_all_agency")):
        assigned_id = requested_assignee or membership.id
    elif membership:
        assigned_id = membership.id
    elif linked_property:
        assignment = PropertyAgentAssignment.objects.filter(property=linked_property).select_related("membership").first()
        assigned_id = assignment.membership_id if assignment else None
    else:
        assigned_id = None
    if assigned_id and not AgencyMembership.objects.filter(
        id=assigned_id, agency_id=agency_id, status=AgencyMembership.Status.ACTIVE
    ).exists():
        raise ValidationDomainError("مشاور تخصیص‌یافته به سرنخ عضو فعال همین آژانس نیست.")
    lead = Lead.objects.all_tenants().create(
        agency_id=agency_id,
        full_name=data["full_name"].strip(),
        phone_number=data["phone_number"].strip(),
        request_type=data.get("request_type", "BUY"),
        property_id=property_id,
        source=data.get("source", "PORTAL"),
        assigned_membership_id=assigned_id,
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
    membership = get_active_membership(user, lead.agency_id)
    if data.get("property_id"):
        from apps.properties.models import Property
        target_property = Property.objects.all_tenants().filter(
            id=data["property_id"], agency_id=lead.agency_id, is_deleted=False
        ).first()
        if not target_property:
            raise ValidationDomainError("ملک مرتبط با سرنخ متعلق به این آژانس نیست.")
        if membership and membership.role.code == "BRANCH_MANAGER" and (
            not membership.branch_id or target_property.branch_id != membership.branch_id
        ):
            raise PermissionDeniedDomainError("مدیر شعبه فقط می‌تواند سرنخ را به ملک شعبه خودش متصل کند.")
    if data.get("assigned_membership_id"):
        from apps.accounts.models import AgencyMembership
        target = AgencyMembership.objects.filter(
            id=data["assigned_membership_id"], agency_id=lead.agency_id,
            status=AgencyMembership.Status.ACTIVE
        ).first()
        if not target:
            raise ValidationDomainError("مشاور تخصیص‌یافته به سرنخ عضو فعال همین آژانس نیست.")
        if membership and membership.role.code == "BRANCH_MANAGER":
            if not membership.branch_id or target.branch_id != membership.branch_id:
                raise PermissionDeniedDomainError("مدیر شعبه فقط می‌تواند سرنخ را به مشاور همان شعبه تخصیص دهد.")
        elif membership and not has_agency_permission(user, lead.agency_id, "customer.view_all_agency") and target.id != membership.id:
            raise PermissionDeniedDomainError("تغییر مشاور تخصیص‌یافته مجاز نیست.")
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


def _normalize_contact(value: str) -> str:
    """Normalize Persian/Arabic digits and phone punctuation for duplicate search."""
    value = (value or "").strip()
    translation = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    value = value.translate(translation)
    return "".join(ch for ch in value if ch.isalnum()).lower()


def find_customer_duplicates(*, user: User, agency_id: Optional[UUID], customer_id: UUID = None, q: str = "") -> list[dict]:
    """Find likely duplicates within the same agency only; exact phone/email prioritized."""
    if not agency_id:
        return []
    source = _resolve_customer(user=user, agency_id=agency_id, customer_id=customer_id) if customer_id else None
    qs = list_customers(user=user, agency_id=agency_id)
    if source:
        qs = qs.exclude(pk=source.pk)
        terms = [source.primary_phone, source.secondary_phone, source.email]
    else:
        terms = [q]
    normalized = {_normalize_contact(t) for t in terms if t and _normalize_contact(t)}
    results = []
    for candidate in qs[:500]:
        candidate_values = {_normalize_contact(candidate.primary_phone), _normalize_contact(candidate.secondary_phone), _normalize_contact(candidate.email)}
        overlap = normalized.intersection(candidate_values - {""})
        name_similarity = SequenceMatcher(None, _normalize_contact(source.full_name), _normalize_contact(candidate.full_name)).ratio() if source else 0.0
        name_match = bool(source and name_similarity >= 0.88)
        if overlap or name_match:
            reasons = ["contact_normalized_match"] if overlap else ["name_similarity"]
            confidence = 0.98 if overlap else round(min(0.94, 0.70 + name_similarity * 0.24), 3)
            results.append({"customer": candidate, "match_reasons": reasons, "confidence": confidence})
    return sorted(results, key=lambda x: x["confidence"], reverse=True)


@transaction.atomic
def transfer_customer(*, user: User, agency_id: Optional[UUID], customer_id: UUID, target_membership_id: UUID, reason: str) -> Customer:
    from apps.accounts.models import AgencyMembership
    from .models import CustomerTransfer
    customer = _resolve_customer(user=user, agency_id=agency_id, customer_id=customer_id)
    if not reason or not reason.strip():
        raise ValidationDomainError("علت انتقال مشتری الزامی است.")
    if not (is_super_admin(user) or has_agency_permission(user, customer.agency_id, "customer.transfer")):
        raise PermissionDeniedDomainError("مجوز انتقال مشتری را ندارید.")
    target = AgencyMembership.objects.filter(id=target_membership_id, agency_id=customer.agency_id, status=AgencyMembership.Status.ACTIVE).first()
    if not target:
        raise ValidationDomainError("مسئول مقصد عضو فعال همین آژانس نیست.")
    if customer.assigned_membership_id == target.id:
        raise ValidationDomainError("مسئول فعلی و مقصد انتقال یکسان هستند.")
    current = get_active_membership(user, customer.agency_id)
    if current and current.role.code == "BRANCH_MANAGER" and (not current.branch_id or target.branch_id != current.branch_id):
        raise PermissionDeniedDomainError("انتقال فقط به اعضای شعبه خود مجاز است.")
    old_id = customer.assigned_membership_id
    CustomerTransfer.objects.create(customer=customer, from_membership_id=old_id, to_membership=target, reason=reason.strip(), created_by=user)
    customer.assigned_membership = target
    customer.updated_by = user
    customer.save(update_fields=["assigned_membership", "updated_by", "updated_at"])
    record_audit_event(action="CUSTOMER_TRANSFERRED", resource_type="Customer", resource_id=str(customer.pk), actor=user, agency_id=customer.agency_id, before_state={"assigned_membership_id": str(old_id) if old_id else None}, after_state={"assigned_membership_id": str(target.pk), "reason": reason.strip()})
    return customer


@transaction.atomic
def merge_customers(*, user: User, agency_id: Optional[UUID], primary_id: UUID, duplicate_id: UUID) -> Customer:
    """Merge duplicate into canonical record, re-pointing FK relations and retaining archive/audit evidence."""
    from django.apps import apps
    primary = _resolve_customer(user=user, agency_id=agency_id, customer_id=primary_id)
    duplicate = _resolve_customer(user=user, agency_id=agency_id, customer_id=duplicate_id)
    if primary.pk == duplicate.pk:
        raise ValidationDomainError("دو پرونده باید متفاوت باشند.")
    if primary.agency_id != duplicate.agency_id:
        raise PermissionDeniedDomainError("ادغام فقط داخل یک آژانس مجاز است.")
    if not (is_super_admin(user) or has_agency_permission(user, primary.agency_id, "customer.merge")):
        raise PermissionDeniedDomainError("مجوز ادغام پرونده مشتری را ندارید.")
    # Keep canonical data; only fill empty fields from duplicate. Never overwrite established values silently.
    for field in ("secondary_phone", "email", "national_id_encrypted"):
        if not getattr(primary, field) and getattr(duplicate, field):
            setattr(primary, field, getattr(duplicate, field))
    primary.tags = list(dict.fromkeys((primary.tags or []) + (duplicate.tags or [])))
    if not primary.secondary_phone and duplicate.primary_phone != primary.primary_phone:
        primary.secondary_phone = duplicate.primary_phone
    primary.save()
    reassigned = []
    # Resolve known one-to-one/unique conflicts before the generic FK rewrite.
    try:
        from apps.crm.models import CustomerPipelineItem
        duplicate_pipeline = CustomerPipelineItem.objects.filter(customer=duplicate).first()
        primary_pipeline = CustomerPipelineItem.objects.filter(customer=primary).first()
        if duplicate_pipeline and primary_pipeline:
            if duplicate_pipeline.notes:
                merged_notes = "\n\n[یادداشت منتقل‌شده از پرونده ادغام‌شده]\n" + duplicate_pipeline.notes
                primary_pipeline.notes = (primary_pipeline.notes or "") + merged_notes
                primary_pipeline.save(update_fields=["notes", "updated_at"])
            duplicate_pipeline.delete()  # canonical stage/assignment wins; duplicate notes are retained
            reassigned.append({"model": "crm.CustomerPipelineItem", "field": "customer", "count": 0, "conflict": "canonical_pipeline_kept_notes_appended"})
    except ImportError:
        pass
    try:
        duplicate_shares = duplicate.shares.all()
        for share in duplicate_shares:
            existing = primary.shares.filter(membership_id=share.membership_id).first()
            if existing:
                # Preserve the more permissive access level, but do not extend an expiry indefinitely.
                if existing.access_level == CustomerShare.AccessLevel.VIEW and share.access_level == CustomerShare.AccessLevel.EDIT:
                    existing.access_level = CustomerShare.AccessLevel.EDIT
                if existing.expires_at and share.expires_at:
                    existing.expires_at = min(existing.expires_at, share.expires_at)
                elif existing.expires_at is None or share.expires_at is None:
                    existing.expires_at = existing.expires_at or share.expires_at
                existing.save(update_fields=["access_level", "expires_at", "updated_at"])
                share.delete()
    except Exception as exc:
        raise ValidationDomainError("تعارض اشتراک مشتری هنگام ادغام حل نشد.") from exc
    for model in apps.get_models():
        if model is Customer or model._meta.proxy:
            continue
        for field in model._meta.fields:
            if getattr(field, "remote_field", None) and field.remote_field.model is Customer:
                try:
                    count = model.objects.filter(**{field.name: duplicate}).update(**{field.name: primary})
                    if count:
                        reassigned.append({"model": model._meta.label, "field": field.name, "count": count})
                except Exception as exc:
                    raise ValidationDomainError(f"ادغام به علت محدودیت رابطه {model._meta.label}.{field.name} انجام نشد.") from exc
    duplicate.is_deleted = True
    duplicate.is_active = False
    duplicate.deleted_at = timezone.now()
    duplicate.deleted_by = user
    duplicate.updated_by = user
    duplicate.save(update_fields=["is_deleted", "is_active", "deleted_at", "deleted_by", "updated_by", "updated_at"])
    record_audit_event(action="CUSTOMER_MERGED", resource_type="Customer", resource_id=str(primary.pk), actor=user, agency_id=primary.agency_id, before_state={"duplicate_id": str(duplicate.pk)}, after_state={"canonical_id": str(primary.pk), "relations_reassigned": reassigned})
    return primary


def customer_timeline(*, user: User, agency_id: Optional[UUID], customer_id: UUID, limit: int = 100) -> list[dict]:
    """Unified, permission-aware activity stream for a customer profile."""
    detail = get_customer_detail(user=user, agency_id=agency_id, customer_id=customer_id)
    customer = detail["customer"]
    events = []
    for x in detail["interactions"]:
        events.append({"type":"interaction", "id":str(x.pk), "title":x.channel, "description":x.summary, "private":x.is_private, "actor": x.membership.user.full_name if x.membership and x.membership.user else (x.created_by.full_name if x.created_by else "سیستم"), "at":x.created_at.isoformat()})
    for x in detail["tasks"]:
        events.append({"type":"task", "id":str(x.pk), "title":x.title, "description":x.status, "actor":x.created_by.full_name if x.created_by else "سیستم", "at":x.created_at.isoformat(), "due_at":x.due_at.isoformat()})
    for x in detail["appointments"]:
        events.append({"type":"appointment", "id":str(x.pk), "title":"بازدید ملک", "description":x.status, "actor":x.agent_membership.user.full_name if x.agent_membership and x.agent_membership.user else "", "at":x.scheduled_start.isoformat()})
    for x in detail["negotiations"]:
        events.append({"type":"negotiation", "id":str(x.pk), "title":"مذاکره", "description":str(x.latest_proposed_price), "actor":x.created_by.full_name if x.created_by else "سیستم", "at":x.created_at.isoformat()})
    for x in detail["contracts"]:
        events.append({"type":"contract", "id":str(x.pk), "title":"قرارداد", "description":f"{x.contract_number} · {x.status}", "actor":x.created_by.full_name if x.created_by else "سیستم", "at":x.created_at.isoformat()})
    for x in detail["documents"]:
        events.append({"type":"document", "id":str(x.pk), "title":"سند پرونده", "description":x.title, "actor":x.created_by.full_name if x.created_by else "سیستم", "at":x.created_at.isoformat()})
    from .models import CustomerTransfer
    for x in CustomerTransfer.objects.filter(customer=customer).select_related("created_by", "from_membership__user", "to_membership__user")[:limit]:
        events.append({"type":"transfer", "id":str(x.pk), "title":"انتقال مسئول مشتری", "description":x.reason, "actor":x.created_by.full_name if x.created_by else "سیستم", "at":x.transferred_at.isoformat(), "from":x.from_membership.user.full_name if x.from_membership else None, "to":x.to_membership.user.full_name})
    # Lead activities are included only if the current user can see the linked lead.
    visible_leads = list_leads(user=user, agency_id=customer.agency_id).filter(converted_customer=customer)
    for lead in visible_leads.prefetch_related("activities__created_by")[:20]:
        for activity in lead.activities.all()[:limit]:
            events.append({"type":"lead", "id":str(activity.pk), "title":"فعالیت سرنخ", "description":activity.note, "actor":activity.created_by.full_name if activity.created_by else "سیستم", "at":activity.created_at.isoformat()})
    return sorted(events, key=lambda item: item["at"], reverse=True)[:limit]


@transaction.atomic
def create_follow_up_task(*, user: User, agency_id: Optional[UUID], customer_id: UUID, assigned_membership_id: UUID, title: str, due_at, ) -> FollowUpTask:
    customer = _resolve_customer(user=user, agency_id=agency_id, customer_id=customer_id)
    if not can_edit_customer(user, customer):
        raise PermissionDeniedDomainError("مجوز ایجاد وظیفه برای مشتری را ندارید.")
    if not title or not title.strip():
        raise ValidationDomainError("عنوان وظیفه الزامی است.")
    from apps.accounts.models import AgencyMembership
    target = AgencyMembership.objects.filter(id=assigned_membership_id, agency_id=customer.agency_id, status=AgencyMembership.Status.ACTIVE).first()
    if not target:
        raise ValidationDomainError("مسئول وظیفه باید عضو فعال همین آژانس باشد.")
    membership = get_active_membership(user, customer.agency_id)
    if membership and membership.role.code == "BRANCH_MANAGER" and (not membership.branch_id or target.branch_id != membership.branch_id):
        raise PermissionDeniedDomainError("تخصیص وظیفه به شعبه دیگر مجاز نیست.")
    return FollowUpTask.objects.all_tenants().create(agency_id=customer.agency_id, customer=customer, assigned_membership=target, title=title.strip(), due_at=due_at, created_by=user)


@transaction.atomic
def update_follow_up_task(*, user: User, agency_id: Optional[UUID], task_id: UUID, status_value: str, ) -> FollowUpTask:
    task = FollowUpTask.objects.all_tenants().filter(id=task_id, agency_id=agency_id, is_deleted=False).first()
    if not task:
        raise NotFoundDomainError("وظیفه پیدا نشد.")
    customer = _resolve_customer(user=user, agency_id=agency_id, customer_id=task.customer_id)
    if not can_edit_customer(user, customer) and task.assigned_membership_id != getattr(get_active_membership(user, customer.agency_id), "id", None):
        raise PermissionDeniedDomainError("مجوز تغییر وظیفه را ندارید.")
    if status_value not in FollowUpTask.Status.values:
        raise ValidationDomainError("وضعیت وظیفه نامعتبر است.")
    if task.status == FollowUpTask.Status.CANCELLED and status_value != task.status:
        raise ValidationDomainError("وظیفه لغوشده قابل بازگشایی نیست؛ وظیفه جدید بسازید.")
    task.status = status_value
    task.completed_at = timezone.now() if status_value == FollowUpTask.Status.COMPLETED else None
    task.updated_by = user
    task.save(update_fields=["status", "completed_at", "updated_by", "updated_at"])
    record_audit_event(action="FOLLOW_UP_TASK_UPDATED", resource_type="FollowUpTask", resource_id=str(task.pk), actor=user, agency_id=task.agency_id, after_state={"status": status_value})
    return task
