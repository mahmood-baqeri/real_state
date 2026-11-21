from typing import Optional
from uuid import UUID
from django.utils import timezone
from apps.accounts.models import User
from apps.payments.models import PaymentGatewayTransaction
from apps.payments.services import initiate_gateway_payment, verify_gateway_payment
from common.exceptions import PermissionDeniedDomainError
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


def list_subscription_plans() -> list[SubscriptionPlan]:
    return list(SubscriptionPlan.objects.filter(is_active=True).order_by("monthly_price"))


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
    billing_cycle: str = "MONTHLY",
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
