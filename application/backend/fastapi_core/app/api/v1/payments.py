from typing import Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context, get_optional_context, require_agency_context
from app.schemas.common import ok

router = APIRouter(prefix="/payments", tags=["Iranian Payment Gateways"])


class GatewayConfigBody(BaseModel):
    provider_key: str
    display_name: str
    description: str = ""
    priority: int = 10
    is_active: bool = True
    is_sandbox: bool = True
    config_json: dict[str, Any] = {}
    credentials: Optional[dict[str, Any]] = None


class PaymentInitiateBody(BaseModel):
    plan_code: str
    billing_cycle: str = "MONTH_1"
    provider_key: Optional[str] = None
    callback_url: str = "/dashboard/subscriptions"
    idempotency_key: Optional[str] = None


class PaymentVerifyBody(BaseModel):
    authority: str
    status: str = "OK"


@router.get("/gateways/active")
async def active_gateways_endpoint(ctx: RequestContext = Depends(get_optional_context)):
    def _op():
        from apps.payments.services import list_public_active_gateways

        return list_public_active_gateways(agency_id=ctx.agency_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/gateways")
async def list_gateways_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.payments.services import list_managed_gateways
        from apps.settings.services import mask_provider_credentials

        return [
            {
                "id": str(c.id),
                "agency_id": str(c.agency_id) if c.agency_id else None,
                "provider_key": c.provider_key,
                "display_name": c.display_name,
                "description": c.description,
                "priority": c.priority,
                "is_active": c.is_active,
                "is_sandbox": c.is_sandbox,
                "config_json": c.config_json,
                "has_credentials": bool(c.encrypted_credentials),
                "masked_credentials": mask_provider_credentials(c),
                "last_checked_at": c.last_checked_at.isoformat() if c.last_checked_at else None,
                "last_check_status": c.last_check_status,
                "last_check_message": c.last_check_message,
            }
            for c in list_managed_gateways(user=ctx.user, agency_id=ctx.agency_id)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/gateways")
async def save_gateway_endpoint(
    body: GatewayConfigBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.payments.services import save_gateway_config
        from apps.settings.services import mask_provider_credentials

        c = save_gateway_config(
            user=ctx.user,
            agency_id=ctx.agency_id,
            data=body.model_dump(exclude_none=True),
        )
        return {
            "id": str(c.id),
            "provider_key": c.provider_key,
            "display_name": c.display_name,
            "is_active": c.is_active,
            "is_sandbox": c.is_sandbox,
            "priority": c.priority,
            "has_credentials": bool(c.encrypted_credentials),
            "masked_credentials": mask_provider_credentials(c),
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/gateways/{config_id}/test")
async def test_gateway_endpoint(
    config_id: UUID, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.payments.services import test_gateway_connection

        return test_gateway_connection(user=ctx.user, agency_id=ctx.agency_id, config_id=config_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/initiate", status_code=201)
async def initiate_payment_endpoint(
    body: PaymentInitiateBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.payments.services import initiate_gateway_payment

        return initiate_gateway_payment(
            user=ctx.user,
            agency_id=ctx.agency_id,
            plan_code=body.plan_code,
            billing_cycle=body.billing_cycle,
            provider_key=body.provider_key,
            callback_url=body.callback_url,
            idempotency_key=body.idempotency_key,
        )

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/verify")
async def verify_payment_endpoint(
    body: PaymentVerifyBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.payments.services import verify_gateway_payment

        tx = verify_gateway_payment(
            user=ctx.user,
            agency_id=ctx.agency_id,
            authority=body.authority,
            callback_status=body.status,
        )
        return {
            "transaction_id": str(tx.id),
            "provider_key": tx.provider_key,
            "authority": tx.authority,
            "order_id": tx.order_id,
            "reference_id": tx.reference_id,
            "amount": str(tx.amount),
            "status": tx.status,
            "error_message": tx.error_message,
            "verified_at": tx.verified_at.isoformat() if tx.verified_at else None,
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/callback/{provider_key}")
async def payment_callback_endpoint(
    provider_key: str,
    Authority: Optional[str] = Query(default=None),
    authority: Optional[str] = Query(default=None),
    trackId: Optional[str] = Query(default=None),
    id: Optional[str] = Query(default=None),
    Status: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default="OK"),
    success: Optional[str] = Query(default=None),
):
    resolved_auth = Authority or authority or trackId or id or ""
    resolved_status = Status or status or ("OK" if success == "1" else "NOK")

    def _op():
        from apps.payments.services import verify_gateway_payment

        tx = verify_gateway_payment(
            user=None,
            agency_id=None,
            authority=resolved_auth,
            callback_status=resolved_status,
        )
        return {
            "transaction_id": str(tx.id),
            "provider_key": tx.provider_key,
            "authority": tx.authority,
            "reference_id": tx.reference_id,
            "status": tx.status,
            "error_message": tx.error_message,
        }

    return ok(await run_django(_op))
