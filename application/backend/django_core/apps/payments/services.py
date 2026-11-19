from decimal import Decimal
from typing import Optional
from uuid import UUID
import uuid as uuid_lib
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.audit.services import record_audit_event
from apps.settings.models import ProviderConfiguration
from apps.settings.services import (
    list_provider_configs,
    parse_provider_credentials,
    resolve_active_provider_config,
    test_provider_config,
    upsert_provider_config,
)
from apps.subscriptions.models import AgencySubscription, SubscriptionPlan
from common.exceptions import ConflictDomainError, NotFoundDomainError, PermissionDeniedDomainError, ValidationDomainError
from common.permissions import get_active_membership, has_agency_permission, is_super_admin
from integrations.registry import PAYMENT_PROVIDERS, get_payment_provider
from .models import PaymentGatewayTransaction


def list_public_active_gateways(*, agency_id: Optional[UUID] = None) -> list[dict]:
    """Lists active payment gateways available for checkout (no secrets exposed)."""
    configs = list(
        ProviderConfiguration.objects.filter(
            category=ProviderConfiguration.Category.PAYMENT,
            is_active=True,
            agency_id__in=[None, agency_id] if agency_id else [None],
        ).order_by("priority", "provider_key")
    )
    seen = set()
    items = []
    for cfg in configs:
        if cfg.provider_key in seen:
            continue
        seen.add(cfg.provider_key)
        adapter_cls = PAYMENT_PROVIDERS.get(cfg.provider_key)
        items.append({
            "id": str(cfg.id),
            "provider_key": cfg.provider_key,
            "display_name": cfg.display_name,
            "description": cfg.description,
            "is_sandbox": cfg.is_sandbox,
            "priority": cfg.priority,
            "required_fields": adapter_cls.required_credential_fields if adapter_cls else [],
            "last_check_status": cfg.last_check_status,
        })
    if not items:
        items.append({
            "id": "sandbox-default",
            "provider_key": "sandbox",
            "display_name": "درگاه آزمایشی داخلی (Sandbox)",
            "description": "شبیه‌سازی امن پرداخت در محیط توسعه",
            "is_sandbox": True,
            "priority": 1,
            "required_fields": [],
            "last_check_status": "READY",
        })
    return items


def list_managed_gateways(*, user: User, agency_id: Optional[UUID]) -> list[ProviderConfiguration]:
    return list_provider_configs(
        user=user, agency_id=agency_id, category=ProviderConfiguration.Category.PAYMENT
    )


def save_gateway_config(*, user: User, agency_id: Optional[UUID], data: dict) -> ProviderConfiguration:
    data = {**data, "category": ProviderConfiguration.Category.PAYMENT}
    if data.get("provider_key") not in PAYMENT_PROVIDERS:
        raise ValidationDomainError("درگاه پرداخت انتخاب‌شده پشتیبانی نمی‌شود.")
    return upsert_provider_config(user=user, agency_id=agency_id, data=data)


def test_gateway_connection(*, user: User, agency_id: Optional[UUID], config_id: UUID) -> dict:
    return test_provider_config(user=user, agency_id=agency_id, config_id=config_id)


@transaction.atomic
def initiate_gateway_payment(
    *,
    user: User,
    agency_id: UUID,
    plan_code: str,
    billing_cycle: str = "MONTHLY",
    provider_key: Optional[str] = None,
    callback_url: str = "/dashboard/subscriptions",
    idempotency_key: Optional[str] = None,
) -> dict:
    if not (is_super_admin(user) or has_agency_permission(user, agency_id, "agency.manage_policy")):
        raise PermissionDeniedDomainError("عدم مجوز خرید یا تمدید اشتراک آژانس.")

    if idempotency_key:
        existing_tx = PaymentGatewayTransaction.objects.filter(
            idempotency_key=idempotency_key, agency_id=agency_id
        ).first()
        if existing_tx:
            return {
                "transaction_id": str(existing_tx.id),
                "authority": existing_tx.authority,
                "order_id": existing_tx.order_id,
                "provider_key": existing_tx.provider_key,
                "redirect_url": f"{existing_tx.callback_url or callback_url}?authority={existing_tx.authority}&status=OK",
                "amount": str(existing_tx.amount),
                "currency": existing_tx.currency_id,
                "subscription_id": str(existing_tx.subscription_id) if existing_tx.subscription_id else None,
                "idempotent_replay": True,
            }

    plan = SubscriptionPlan.objects.filter(code=plan_code, is_active=True).first()
    if not plan:
        raise NotFoundDomainError("پلن اشتراک یافت نشد.")

    # Resolve gateway config & enforce active gateway rule
    if provider_key:
        cfg = resolve_active_provider_config(
            category=ProviderConfiguration.Category.PAYMENT,
            agency_id=agency_id,
            provider_key=provider_key,
        )
        resolved_key = provider_key
    else:
        cfg = resolve_active_provider_config(
            category=ProviderConfiguration.Category.PAYMENT,
            agency_id=agency_id,
        )
        resolved_key = cfg.provider_key if cfg else "sandbox"

    if cfg and not cfg.is_active:
        raise ValidationDomainError("درگاه پرداخت انتخاب‌شده در حال حاضر غیرفعال است.")

    adapter = get_payment_provider(resolved_key)
    creds = parse_provider_credentials(cfg)
    is_sandbox = cfg.is_sandbox if cfg else True

    # Server determines authoritative amount from DB plan — never from client input!
    amount = plan.annual_price if billing_cycle == "ANNUAL" else plan.monthly_price
    if amount <= Decimal("0"):
        raise ValidationDomainError("مبلغ پلن اشتراک نامعتبر است.")

    now = timezone.now()
    days = 365 if billing_cycle == "ANNUAL" else 30
    sub = AgencySubscription.objects.create(
        agency_id=agency_id,
        plan=plan,
        billing_cycle=billing_cycle,
        starts_at=now,
        expires_at=now + timedelta_days(days),
        status=AgencySubscription.Status.TRIAL,
        created_by=user,
    )

    order_id = f"BM-{now.strftime('%Y%m%d')}-{uuid_lib.uuid4().hex[:8].upper()}"
    init_res = adapter.create_payment_intent(
        amount=amount,
        currency=plan.currency_id,
        callback_url=callback_url,
        metadata={
            "description": f"اشتراک {plan.name_fa} ({billing_cycle}) — کد سفارش {order_id}",
            "order_id": order_id,
            "mobile": user.phone_number,
        },
        credentials=creds,
        is_sandbox=is_sandbox,
    )

    tx = PaymentGatewayTransaction.objects.create(
        agency_id=agency_id,
        subscription=sub,
        provider_key=adapter.provider_key,
        authority=init_res.authority,
        order_id=order_id,
        idempotency_key=idempotency_key,
        callback_url=callback_url,
        currency=plan.currency,
        amount=amount,
        status=PaymentGatewayTransaction.Status.INITIATED,
        raw_payload=init_res.raw_response,
        created_by=user,
    )
    record_audit_event(
        action="PAYMENT_INITIATED",
        resource_type="PaymentGatewayTransaction",
        resource_id=str(tx.id),
        actor=user,
        agency_id=agency_id,
        after_state={
            "provider_key": tx.provider_key,
            "order_id": order_id,
            "amount": str(tx.amount),
            "is_sandbox": is_sandbox,
        },
    )
    return {
        "transaction_id": str(tx.id),
        "authority": tx.authority,
        "order_id": tx.order_id,
        "provider_key": tx.provider_key,
        "is_sandbox": is_sandbox,
        "redirect_url": init_res.redirect_url,
        "amount": str(tx.amount),
        "currency": tx.currency_id,
        "subscription_id": str(sub.id),
    }


def timedelta_days(days: int):
    from datetime import timedelta
    return timedelta(days=days)


@transaction.atomic
def verify_gateway_payment(
    *,
    user: Optional[User],
    agency_id: Optional[UUID],
    authority: str,
    callback_status: str = "OK",
) -> PaymentGatewayTransaction:
    qs = PaymentGatewayTransaction.objects.select_for_update().filter(authority=authority)
    if agency_id:
        qs = qs.filter(agency_id=agency_id)
    tx = qs.first()
    if not tx:
        raise NotFoundDomainError("تراکنش پرداخت یافت نشد.")

    if user and user.is_authenticated and not is_super_admin(user):
        if tx.agency_id and not get_active_membership(user, tx.agency_id):
            raise PermissionDeniedDomainError("عدم دسترسی به تایید تراکنش این آژانس.")

    # Idempotent double-verification guard: already paid transactions return cleanly without double charging
    if tx.status == PaymentGatewayTransaction.Status.PAID:
        return tx

    if (callback_status or "OK").upper() not in ("OK", "100", "PAID", "SUCCESS"):
        tx.status = PaymentGatewayTransaction.Status.FAILED
        tx.error_message = "پرداخت توسط کاربر یا درگاه لغو شد."
        tx.verified_at = timezone.now()
        tx.save(update_fields=["status", "error_message", "verified_at", "updated_at"])
        return tx

    cfg = resolve_active_provider_config(
        category=ProviderConfiguration.Category.PAYMENT,
        agency_id=tx.agency_id,
        provider_key=tx.provider_key,
    )
    adapter = get_payment_provider(tx.provider_key)
    creds = parse_provider_credentials(cfg)
    is_sandbox = cfg.is_sandbox if cfg else True

    res = adapter.verify_payment(
        authority=tx.authority,
        expected_amount=tx.amount,
        currency=tx.currency_id,
        credentials=creds,
        is_sandbox=is_sandbox,
        order_id=tx.order_id,
    )
    if res.is_paid and res.verified_amount == tx.amount:
        tx.status = PaymentGatewayTransaction.Status.PAID
        tx.reference_id = res.reference_id
        tx.error_message = ""
        tx.verified_at = timezone.now()
        tx.verified_by = user if (user and user.is_authenticated) else None
        tx.raw_payload = res.raw_response
        tx.save(
            update_fields=[
                "status",
                "reference_id",
                "error_message",
                "verified_at",
                "verified_by",
                "raw_payload",
                "updated_at",
            ]
        )
        if tx.subscription:
            tx.subscription.status = AgencySubscription.Status.ACTIVE
            tx.subscription.save(update_fields=["status", "updated_at"])
        record_audit_event(
            action="SUBSCRIPTION_PAYMENT_VERIFIED",
            resource_type="PaymentGatewayTransaction",
            resource_id=str(tx.id),
            actor=user if (user and user.is_authenticated) else None,
            agency_id=tx.agency_id,
            after_state={"status": "PAID", "reference_id": tx.reference_id, "provider_key": tx.provider_key},
        )
    else:
        tx.status = PaymentGatewayTransaction.Status.FAILED
        tx.error_message = res.error_message or "تایید پرداخت در درگاه ناموفق بود."
        tx.raw_payload = res.raw_response
        tx.verified_at = timezone.now()
        tx.save(update_fields=["status", "error_message", "raw_payload", "verified_at", "updated_at"])
    return tx
