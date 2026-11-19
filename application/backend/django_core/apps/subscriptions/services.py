# Path: backend/django_core/apps/subscriptions/services.py

from datetime import timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.audit.services import record_audit_event
from apps.payments.models import PaymentGatewayTransaction
from common.exceptions import NotFoundDomainError, PermissionDeniedDomainError
from common.permissions import get_active_membership, has_agency_permission, is_super_admin
from integrations.registry import get_payment_provider
from .models import AgencySubscription, SubscriptionPlan


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


@transaction.atomic
def initiate_subscription_payment(
    *, user: User, agency_id: UUID, plan_code: str, billing_cycle: str = "MONTHLY", provider_key: str = "sandbox"
) -> dict:
    if not (is_super_admin(user) or has_agency_permission(user, agency_id, "agency.manage_policy")):
        raise PermissionDeniedDomainError("عدم مجوز خرید یا تمدید اشتراک آژانس.")
    plan = SubscriptionPlan.objects.filter(code=plan_code, is_active=True).first()
    if not plan:
        raise NotFoundDomainError("پلن اشتراک یافت نشد.")

    amount = plan.annual_price if billing_cycle == "ANNUAL" else plan.monthly_price
    now = timezone.now()
    days = 365 if billing_cycle == "ANNUAL" else 30

    sub = AgencySubscription.objects.create(
        agency_id=agency_id,
        plan=plan,
        billing_cycle=billing_cycle,
        starts_at=now,
        expires_at=now + timedelta(days=days),
        status=AgencySubscription.Status.TRIAL,
        created_by=user,
    )

    provider = get_payment_provider(provider_key)
    init_res = provider.create_payment_intent(
        amount=amount,
        currency=plan.currency_id,
        callback_url="/dashboard/subscriptions",
        metadata={"description": f"اشتراک {plan.name_fa} ({billing_cycle})"},
    )

    tx = PaymentGatewayTransaction.objects.create(
        agency_id=agency_id,
        subscription=sub,
        provider_key=provider.provider_key,
        authority=init_res.authority,
        currency=plan.currency,
        amount=amount,
        status=PaymentGatewayTransaction.Status.INITIATED,
        created_by=user,
    )
    return {
        "transaction_id": str(tx.id),
        "authority": tx.authority,
        "redirect_url": init_res.redirect_url,
        "amount": str(tx.amount),
        "currency": tx.currency_id,
        "subscription_id": str(sub.id),
    }


@transaction.atomic
def verify_subscription_payment(*, user: User, agency_id: UUID, authority: str) -> PaymentGatewayTransaction:
    tx = PaymentGatewayTransaction.objects.select_for_update().filter(
        authority=authority, agency_id=agency_id
    ).first()
    if not tx:
        raise NotFoundDomainError("تراکنش پرداخت یافت نشد.")
    provider = get_payment_provider(tx.provider_key)
    res = provider.verify_payment(authority=tx.authority, expected_amount=tx.amount, currency=tx.currency_id)
    if res.is_paid:
        tx.status = PaymentGatewayTransaction.Status.PAID
        tx.reference_id = res.reference_id
        tx.raw_payload = res.raw_response
        tx.save(update_fields=["status", "reference_id", "raw_payload", "updated_at"])
        if tx.subscription:
            tx.subscription.status = AgencySubscription.Status.ACTIVE
            tx.subscription.save(update_fields=["status", "updated_at"])
        record_audit_event(
            action="SUBSCRIPTION_PAYMENT_VERIFIED",
            resource_type="PaymentGatewayTransaction",
            resource_id=str(tx.id),
            actor=user,
            agency_id=agency_id,
        )
    else:
        tx.status = PaymentGatewayTransaction.Status.FAILED
        tx.save(update_fields=["status", "updated_at"])
    return tx
