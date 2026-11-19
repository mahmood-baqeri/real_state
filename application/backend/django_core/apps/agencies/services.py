from decimal import Decimal
from typing import Optional
from uuid import UUID
from django.db import models, transaction
from apps.accounts.models import AgencyMembership, Role, User
from apps.audit.services import record_audit_event
from apps.branches.models import Branch
from common.exceptions import ConflictDomainError, NotFoundDomainError, PermissionDeniedDomainError
from common.permissions import get_active_membership, has_agency_permission, is_super_admin
from .models import Agency, AgencyAccessPolicy, AgencyCooperation


def list_agencies_for_user(user: Optional[User]):
    qs = Agency.objects.filter(is_deleted=False).select_related("owner_user", "country", "default_currency")
    if is_super_admin(user):
        return qs
    if user and user.is_authenticated:
        member_ids = user.memberships.filter(status="ACTIVE").values_list("agency_id", flat=True)
        return qs.filter(models.Q(id__in=member_ids) | models.Q(status=Agency.Status.ACTIVE)).distinct()
    return qs.filter(status=Agency.Status.ACTIVE)


def get_agency_for_user(user: Optional[User], agency_id: UUID) -> Agency:
    agency = list_agencies_for_user(user).filter(id=agency_id).first()
    if not agency:
        raise NotFoundDomainError("آژانس مورد نظر یافت نشد.")
    return agency


@transaction.atomic
def create_agency(
    *,
    owner: User,
    name: str,
    slug: str,
    registration_number: str = "",
    tax_id: str = "",
    phone: str = "",
    email: str = "",
    description: str = "",
    country_id: str = "IR",
    default_currency_id: str = "IRT",
    default_calendar: str = "jalali",
    timezone_str: str = "Asia/Tehran",
    area_unit: str = "SQM",
) -> Agency:
    clean_slug = slug.strip().lower()
    if Agency.objects.filter(slug=clean_slug).exists():
        raise ConflictDomainError("شناسه یکتای آژانس (Slug) قبلاً ثبت شده است.")

    status_val = Agency.Status.ACTIVE if is_super_admin(owner) else Agency.Status.PENDING_REVIEW
    agency = Agency.objects.create(
        name=name.strip(),
        slug=clean_slug,
        registration_number=registration_number.strip(),
        tax_id=tax_id.strip(),
        phone=phone.strip(),
        email=email.strip(),
        description=description.strip(),
        country_id=country_id,
        default_currency_id=default_currency_id,
        default_calendar=default_calendar,
        timezone=timezone_str,
        area_unit=area_unit,
        owner_user=owner,
        status=status_val,
        created_by=owner,
    )
    AgencyAccessPolicy.objects.create(agency=agency)
    Branch.objects.all_tenants().create(
        agency=agency,
        name="شعبه مرکزی",
        code="MAIN-01",
        country_id=country_id,
        is_main=True,
        created_by=owner,
    )
    manager_role = Role.objects.filter(code="AGENCY_MANAGER", is_system_role=True).first()
    if manager_role:
        AgencyMembership.objects.get_or_create(
            user=owner,
            agency=agency,
            defaults={"role": manager_role, "status": AgencyMembership.Status.ACTIVE},
        )
    if owner.platform_role == User.PlatformRole.CUSTOMER:
        owner.platform_role = User.PlatformRole.AGENCY_USER
        owner.save(update_fields=["platform_role", "updated_at"])

    record_audit_event(
        action="AGENCY_CREATED",
        resource_type="Agency",
        resource_id=str(agency.id),
        actor=owner,
        agency_id=agency.id,
    )
    return agency


@transaction.atomic
def update_agency_status(*, actor: User, agency_id: UUID, new_status: str) -> Agency:
    if not is_super_admin(actor):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به تغییر وضعیت آژانس است.")
    agency = Agency.objects.filter(id=agency_id, is_deleted=False).first()
    if not agency:
        raise NotFoundDomainError("آژانس یافت نشد.")
    prev = agency.status
    agency.status = new_status
    agency.updated_by = actor
    agency.save(update_fields=["status", "updated_by", "updated_at"])
    record_audit_event(
        action="AGENCY_STATUS_CHANGED",
        resource_type="Agency",
        resource_id=str(agency.id),
        actor=actor,
        agency_id=agency.id,
        before_state={"status": prev},
        after_state={"status": new_status},
    )
    return agency


def get_access_policy(*, actor: User, agency_id: UUID) -> AgencyAccessPolicy:
    if not (is_super_admin(actor) or get_active_membership(actor, agency_id)):
        raise PermissionDeniedDomainError("شما عضو این آژانس نیستید.")
    policy, _ = AgencyAccessPolicy.objects.get_or_create(agency_id=agency_id)
    return policy


@transaction.atomic
def update_access_policy(*, actor: User, agency_id: UUID, updates: dict) -> AgencyAccessPolicy:
    if not (is_super_admin(actor) or has_agency_permission(actor, agency_id, "agency.manage_policy")):
        raise PermissionDeniedDomainError("شما مجوز مدیریت سیاست‌های دسترسی آژانس را ندارید.")
    policy, _ = AgencyAccessPolicy.objects.get_or_create(agency_id=agency_id)
    policy_fields = [
        "property_view_scope",
        "property_edit_scope",
        "customer_view_scope",
        "customer_edit_scope",
        "owner_pii_visibility",
        "negotiation_visibility",
        "contract_visibility",
        "financial_visibility",
        "commission_visibility",
        "agent_performance_visibility",
    ]
    before = {k: getattr(policy, k) for k in policy_fields}
    for k in policy_fields:
        if k in updates and updates[k] is not None:
            setattr(policy, k, updates[k])
    policy.updated_by = actor
    policy.save()
    after = {k: getattr(policy, k) for k in policy_fields}
    record_audit_event(
        action="AGENCY_ACCESS_POLICY_UPDATED",
        resource_type="AgencyAccessPolicy",
        resource_id=str(policy.id),
        actor=actor,
        agency_id=agency_id,
        before_state=before,
        after_state=after,
    )
    return policy


def list_branches(*, actor: Optional[User], agency_id: UUID) -> list[Branch]:
    return list(Branch.objects.all_tenants().filter(agency_id=agency_id, is_active=True).order_by("-is_main", "name"))


@transaction.atomic
def create_branch(*, actor: User, agency_id: UUID, data: dict) -> Branch:
    if not (is_super_admin(actor) or has_agency_permission(actor, agency_id, "agency.manage_branches")):
        raise PermissionDeniedDomainError("عدم دسترسی ایجاد شعبه.")
    if Branch.objects.all_tenants().filter(agency_id=agency_id, code=data["code"]).exists():
        raise ConflictDomainError("شعبه‌ای با این کد در آژانس موجود است.")
    branch = Branch.objects.all_tenants().create(
        agency_id=agency_id,
        name=data["name"],
        code=data["code"],
        country_id=data.get("country_id", "IR"),
        province=data.get("province", ""),
        city=data.get("city", ""),
        address=data.get("address", ""),
        phone=data.get("phone", ""),
        is_main=bool(data.get("is_main", False)),
        created_by=actor,
    )
    return branch


def list_agency_members(*, actor: User, agency_id: UUID) -> list[AgencyMembership]:
    if not (is_super_admin(actor) or get_active_membership(actor, agency_id)):
        raise PermissionDeniedDomainError("دسترسی به اعضای این آژانس مجاز نیست.")
    return list(
        AgencyMembership.objects.select_related("user", "role", "branch")
        .filter(agency_id=agency_id)
        .order_by("role__code", "user__last_name")
    )


def list_cooperations(*, actor: User, agency_id: UUID) -> list[AgencyCooperation]:
    if not (is_super_admin(actor) or get_active_membership(actor, agency_id)):
        raise PermissionDeniedDomainError("عدم دسترسی به همکاری‌های آژانس.")
    return list(
        AgencyCooperation.objects.select_related("requester_agency", "provider_agency")
        .filter(models.Q(requester_agency_id=agency_id) | models.Q(provider_agency_id=agency_id))
        .order_by("-created_at")
    )


@transaction.atomic
def request_cooperation(
    *, actor: User, requester_agency_id: UUID, provider_agency_id: UUID, split_percent: Decimal
) -> AgencyCooperation:
    if not (is_super_admin(actor) or has_agency_permission(actor, requester_agency_id, "agency.manage_policy")):
        raise PermissionDeniedDomainError("عدم مجوز ثبت درخواست همکاری بین‌آژانسی.")
    if requester_agency_id == provider_agency_id:
        raise ConflictDomainError("آژانس مبدأ و مقصد نمی‌توانند یکسان باشند.")
    coop, _ = AgencyCooperation.objects.update_or_create(
        requester_agency_id=requester_agency_id,
        provider_agency_id=provider_agency_id,
        defaults={
            "default_split_percent": split_percent,
            "status": AgencyCooperation.Status.PENDING,
            "created_by": actor,
        },
    )
    return coop


@transaction.atomic
def respond_cooperation(*, actor: User, agency_id: UUID, coop_id: UUID, status_value: str) -> AgencyCooperation:
    coop = AgencyCooperation.objects.filter(id=coop_id).first()
    if not coop or (coop.provider_agency_id != agency_id and not is_super_admin(actor)):
        raise NotFoundDomainError("قرارداد همکاری یافت نشد.")
    if not (is_super_admin(actor) or has_agency_permission(actor, agency_id, "agency.manage_policy")):
        raise PermissionDeniedDomainError("عدم مجوز تأیید یا رد همکاری.")
    coop.status = status_value
    coop.updated_by = actor
    coop.save(update_fields=["status", "updated_by", "updated_at"])
    return coop
