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
