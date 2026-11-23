from datetime import timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.agencies.models import Agency
from apps.audit.services import record_audit_event
from apps.payments.models import PaymentGatewayTransaction
from apps.payments.services import initiate_gateway_payment, verify_gateway_payment
from common.exceptions import (
    ConflictDomainError,
    NotFoundDomainError,
    PermissionDeniedDomainError,
    ValidationDomainError,
)
from common.permissions import get_active_membership, is_super_admin
from .models import AgencySubscription, SubscriptionPlan


def get_active_agency_subscription(agency_id: UUID) -> Optional[AgencySubscription]:
    now = timezone.now()
    return (
        AgencySubscription.objects.select_related("plan")
        .filter(
            agency_id=agency_id,
            status__in=[AgencySubscription.Status.ACTIVE, AgencySubscription.Status.TRIAL],
            expires_at__gte=now,
        )
        .order_by("-expires_at")
        .first()
    )


def enforce_agency_quota(
    *,
    agency_id: UUID,
    quota_field: str,
    current_count: int,
    actor: Optional[User] = None,
    label_fa: str = "مورد",
) -> None:
    if actor and is_super_admin(actor):
        return
    active_sub = get_active_agency_subscription(agency_id)
    if not active_sub or not active_sub.plan:
        return
    limit = int(getattr(active_sub.plan, quota_field, 0) or 0)
    if limit > 0 and current_count >= limit:
        raise PermissionDeniedDomainError(
            f"سقف مجاز {label_fa} در پلن اشتراک فعلی شما ({limit}) تکمیل شده است. لطفاً پلن خود را ارتقا دهید."
        )


def list_subscription_plans(*, include_inactive: bool = False) -> list[SubscriptionPlan]:
    qs = SubscriptionPlan.objects.all()
    if not include_inactive:
        qs = qs.filter(is_active=True)
    return list(qs.order_by("monthly_price"))


@transaction.atomic
def create_subscription_plan(*, actor: User, data: dict) -> SubscriptionPlan:
    if not is_super_admin(actor):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به تعریف پلن اشتراک است.")
    code = str(data.get("code") or "").strip().upper()
    if not code:
        raise ValidationDomainError("کد پلن اشتراک الزامی است.")
    if SubscriptionPlan.objects.filter(code=code).exists():
        raise ConflictDomainError("پلن اشتراکی با این کد قبلاً ثبت شده است.")
    plan = SubscriptionPlan.objects.create(
        code=code,
        name_fa=str(data.get("name_fa") or code).strip(),
        name_en=str(data.get("name_en") or code).strip(),
        currency_id=str(data.get("currency_id") or "IRT"),
        monthly_price=Decimal(str(data.get("monthly_price") or "0")),
        annual_price=Decimal(str(data.get("annual_price") or "0")),
        max_agents=int(data.get("max_agents") or 5),
        max_branches=int(data.get("max_branches") or 1),
        max_active_listings=int(data.get("max_active_listings") or 50),
        features_json=dict(data.get("features_json") or {}),
        is_active=bool(data.get("is_active", True)),
        created_by=actor,
    )
    record_audit_event(
        action="SUBSCRIPTION_PLAN_CREATED",
        resource_type="SubscriptionPlan",
        resource_id=str(plan.id),
        actor=actor,
        after_state={"code": plan.code},
    )
    return plan


@transaction.atomic
def update_subscription_plan(*, actor: User, plan_id: UUID, data: dict) -> SubscriptionPlan:
    if not is_super_admin(actor):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به ویرایش پلن اشتراک است.")
    plan = SubscriptionPlan.objects.filter(id=plan_id).first()
    if not plan:
        raise NotFoundDomainError("پلن اشتراک یافت نشد.")
    for field in ("name_fa", "name_en", "currency_id"):
        if field in data and data[field] is not None:
            setattr(plan, field, str(data[field]).strip())
    for dec_field in ("monthly_price", "annual_price"):
        if dec_field in data and data[dec_field] is not None:
            setattr(plan, dec_field, Decimal(str(data[dec_field])))
    for int_field in ("max_agents", "max_branches", "max_active_listings"):
        if int_field in data and data[int_field] is not None:
            setattr(plan, int_field, int(data[int_field]))
    if "features_json" in data and data["features_json"] is not None:
        plan.features_json = dict(data["features_json"])
    if "is_active" in data and data["is_active"] is not None:
        plan.is_active = bool(data["is_active"])
    plan.updated_by = actor
    plan.save()
    return plan


@transaction.atomic
def deactivate_subscription_plan(*, actor: User, plan_id: UUID) -> SubscriptionPlan:
    if not is_super_admin(actor):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به غیرفعال‌سازی پلن اشتراک است.")
    plan = SubscriptionPlan.objects.filter(id=plan_id).first()
    if not plan:
        raise NotFoundDomainError("پلن اشتراک یافت نشد.")
    plan.is_active = False
    plan.updated_by = actor
    plan.save(update_fields=["is_active", "updated_by", "updated_at"])
    return plan


@transaction.atomic
def assign_or_create_agency_subscription(*, actor: User, data: dict) -> AgencySubscription:
    if not is_super_admin(actor):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به تخصیص دستی اشتراک به آژانس است.")
    agency = Agency.objects.filter(id=data["agency_id"], is_deleted=False).first()
    if not agency:
        raise NotFoundDomainError("آژانس یافت نشد.")
    plan = SubscriptionPlan.objects.filter(code=str(data["plan_code"]).strip().upper()).first()
    if not plan:
        raise NotFoundDomainError("پلن اشتراک یافت نشد.")
    status_val = str(data.get("status") or AgencySubscription.Status.ACTIVE)
    if status_val not in AgencySubscription.Status.values:
        raise ValidationDomainError("وضعیت اشتراک نامعتبر است.")
    cycle = str(data.get("billing_cycle") or "MONTH_1").upper()
    cycle_months = {"MONTH_1": 1, "MONTH_2": 2, "MONTH_3": 3, "MONTH_6": 6, "MONTH_12": 12, "MONTHLY": 1, "ANNUAL": 12}
    if cycle not in cycle_months:
        raise ValidationDomainError("مدت اشتراک نامعتبر است؛ یکی از دوره‌های ۱، ۲، ۳، ۶ یا ۱۲ ماه را انتخاب کنید.")
    duration_days = max(1, int(data.get("duration_days") or cycle_months[cycle] * 30))
    now = timezone.now()
    sub = AgencySubscription.objects.create(
        agency=agency,
        plan=plan,
        billing_cycle=cycle,
        starts_at=now,
        expires_at=now + timedelta(days=duration_days),
        status=status_val,
        created_by=actor,
    )
    record_audit_event(
        action="AGENCY_SUBSCRIPTION_ASSIGNED",
        resource_type="AgencySubscription",
        resource_id=str(sub.id),
        actor=actor,
        agency_id=agency.id,
        after_state={"plan_code": plan.code, "status": sub.status, "expires_at": sub.expires_at.isoformat()},
    )
    return sub


@transaction.atomic
def update_agency_subscription(*, actor: User, sub_id: UUID, data: dict) -> AgencySubscription:
    if not is_super_admin(actor):
        raise PermissionDeniedDomainError("فقط مدیر کل مجاز به تمدید یا تغییر اشتراک آژانس است.")
    sub = AgencySubscription.objects.select_related("agency", "plan").filter(id=sub_id).first()
    if not sub:
        raise NotFoundDomainError("اشتراک آژانس یافت نشد.")
    if "plan_code" in data and data["plan_code"]:
        plan = SubscriptionPlan.objects.filter(code=str(data["plan_code"]).strip().upper()).first()
        if not plan:
            raise NotFoundDomainError("پلن اشتراک یافت نشد.")
        sub.plan = plan
    if "billing_cycle" in data and data["billing_cycle"]:
        sub.billing_cycle = str(data["billing_cycle"])
    if "status" in data and data["status"]:
        if data["status"] not in AgencySubscription.Status.values:
            raise ValidationDomainError("وضعیت اشتراک نامعتبر است.")
        sub.status = data["status"]
    if "extend_days" in data and data["extend_days"]:
        days = int(data["extend_days"])
        base_dt = max(sub.expires_at, timezone.now())
        sub.expires_at = base_dt + timedelta(days=days)
        if sub.status in (AgencySubscription.Status.EXPIRED, AgencySubscription.Status.PAST_DUE):
            sub.status = AgencySubscription.Status.ACTIVE
    sub.updated_by = actor
    sub.save()
    record_audit_event(
        action="AGENCY_SUBSCRIPTION_UPDATED",
        resource_type="AgencySubscription",
        resource_id=str(sub.id),
        actor=actor,
        agency_id=sub.agency_id,
        after_state={"plan": sub.plan.code, "status": sub.status, "expires_at": sub.expires_at.isoformat()},
    )
    return sub


def list_agency_subscriptions(*, user: User, agency_id: Optional[UUID]) -> list[AgencySubscription]:
    qs = AgencySubscription.objects.select_related("agency", "plan").order_by("-expires_at")
    if is_super_admin(user) and not agency_id:
        return list(qs)
    if not agency_id or not (is_super_admin(user) or get_active_membership(user, agency_id)):
        raise PermissionDeniedDomainError("عدم دسترسی به اشتراک‌های آژانس.")
    return list(qs.filter(agency_id=agency_id))


def list_payment_transactions(*, user: User, agency_id: Optional[UUID]) -> list[PaymentGatewayTransaction]:
    qs = PaymentGatewayTransaction.objects.select_related("agency", "subscription__plan", "currency").order_by("-created_at")
    if is_super_admin(user) and not agency_id:
        return list(qs)
    if not agency_id or not (is_super_admin(user) or get_active_membership(user, agency_id)):
        raise PermissionDeniedDomainError("عدم دسترسی به تراکنش‌های درگاه پرداخت.")
    return list(qs.filter(agency_id=agency_id))


def initiate_subscription_payment(
    *,
    user: User,
    agency_id: UUID,
    plan_code: str,
    billing_cycle: str = "MONTH_1",
    provider_key: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> dict:
    return initiate_gateway_payment(
        user=user,
        agency_id=agency_id,
        plan_code=plan_code,
        billing_cycle=billing_cycle,
        provider_key=provider_key,
        callback_url="/dashboard/subscriptions",
        idempotency_key=idempotency_key,
    )


def verify_subscription_payment(
    *, user: User, agency_id: UUID, authority: str, callback_status: str = "OK"
) -> PaymentGatewayTransaction:
    return verify_gateway_payment(
        user=user,
        agency_id=agency_id,
        authority=authority,
        callback_status=callback_status,
    )
