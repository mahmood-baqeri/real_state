from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context, require_agency_context
from app.schemas.common import ok

router = APIRouter(tags=["Subscriptions & Payments"])


class CheckoutBody(BaseModel):
    plan_code: str
    billing_cycle: str = "MONTHLY"
    provider_key: str = "sandbox"


class VerifyBody(BaseModel):
    authority: str


@router.get("/subscriptions/plans")
async def list_plans_endpoint():
    def _op():
        from apps.subscriptions.services import list_subscription_plans

        return [
            {
                "id": str(p.id),
                "code": p.code,
                "name_fa": p.name_fa,
                "name_en": p.name_en,
                "currency": p.currency_id,
                "monthly_price": str(p.monthly_price),
                "annual_price": str(p.annual_price),
                "max_agents": p.max_agents,
                "max_properties": p.max_active_listings,
                "max_active_listings": p.max_active_listings,
                "max_branches": p.max_branches,
                "features": p.features_json,
            }
            for p in list_subscription_plans()
        ]

    return ok(await run_django(_op))


@router.get("/subscriptions/current")
async def list_current_subscriptions_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.subscriptions.services import list_agency_subscriptions

        return [
            {
                "id": str(s.id),
                "agency_id": str(s.agency_id),
                "agency_name": s.agency.name,
                "plan_code": s.plan.code,
                "plan_name_fa": s.plan.name_fa,
                "billing_cycle": s.billing_cycle,
                "starts_at": s.starts_at.isoformat(),
                "expires_at": s.expires_at.isoformat(),
                "status": s.status,
            }
            for s in list_agency_subscriptions(user=ctx.user, agency_id=ctx.agency_id)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/subscriptions/checkout", status_code=201)
async def checkout_subscription_endpoint(
    body: CheckoutBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.subscriptions.services import initiate_subscription_payment

        return initiate_subscription_payment(
            user=ctx.user,
            agency_id=ctx.agency_id,
            plan_code=body.plan_code,
            billing_cycle=body.billing_cycle,
            provider_key=body.provider_key,
        )

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/subscriptions/verify")
async def verify_subscription_endpoint(
    body: VerifyBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.subscriptions.services import verify_subscription_payment

        tx = verify_subscription_payment(
            user=ctx.user,
            agency_id=ctx.agency_id,
            authority=body.authority,
        )
        return {
            "transaction_id": str(tx.id),
            "authority": tx.authority,
            "status": tx.status,
            "reference_id": tx.reference_id,
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/payments/transactions")
async def list_transactions_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.subscriptions.services import list_payment_transactions

        return [
            {
                "id": str(t.id),
                "agency_name": t.agency.name,
                "provider_key": t.provider_key,
                "authority": t.authority,
                "reference_id": t.reference_id,
                "currency": t.currency_id,
                "amount": str(t.amount),
                "status": t.status,
                "created_at": t.created_at.isoformat(),
            }
            for t in list_payment_transactions(user=ctx.user, agency_id=ctx.agency_id)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id))
