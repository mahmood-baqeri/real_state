from decimal import Decimal
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, require_agency_context
from app.schemas.common import ok

router = APIRouter(prefix="/commissions", tags=["Commissions & Policies"])


class CommissionPolicyCreateBody(BaseModel):
    name: str
    deal_type_id: str
    formula_type: str = "PERCENT"
    gross_rate_percent: Decimal = Decimal("1.0000")
    fixed_amount: Decimal = Decimal("0.00")
    tax_rate_percent: Decimal = Decimal("10.0000")
    platform_share_percent: Decimal = Decimal("0.0000")
    agency_house_percent: Decimal = Decimal("50.0000")
    primary_agent_percent: Decimal = Decimal("50.0000")
    co_agent_split_ratio: Decimal = Decimal("50.0000")
    rules_json: dict = Field(default_factory=dict)


class CommissionCalculateBody(BaseModel):
    deal_id: UUID
    policy_version_id: Optional[UUID] = None
    discount_amount: Decimal = Decimal("0.00")


class CommissionStatusBody(BaseModel):
    status: str


def _ser_commission(dc) -> dict:
    return {
        "id": str(dc.id),
        "deal_id": str(dc.deal_id),
        "deal_code": dc.deal.deal_code,
        "property_title": dc.deal.property.title,
        "currency": dc.currency_id,
        "base_amount": str(dc.base_amount),
        "gross_commission": str(dc.gross_commission),
        "discount_amount": str(dc.discount_amount),
        "tax_amount": str(dc.tax_amount),
        "net_distributable": str(dc.net_distributable),
        "status": dc.status,
        "shares": [
            {
                "id": str(s.id),
                "beneficiary_type": s.beneficiary_type,
                "beneficiary_name": s.beneficiary_membership.user.full_name
                if s.beneficiary_membership
                else ("پلتفرم" if s.beneficiary_type == "PLATFORM" else "آژانس"),
                "share_percent_of_net": str(s.share_percent_of_net),
                "calculated_amount": str(s.calculated_amount),
                "is_included_in_payroll": s.is_included_in_payroll,
            }
            for s in dc.shares.all()
        ],
        "created_at": dc.created_at.isoformat(),
    }


@router.get("")
async def list_commissions_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.commissions.services import list_commissions
        from common.pagination import paginate_queryset

        qs = list_commissions(user=ctx.user, agency_id=ctx.agency_id)
        return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser_commission)

    items, meta = await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None)
    return ok(items, meta=meta)


@router.get("/policies")
async def list_policies_endpoint(ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.commissions.services import list_commission_policies

        return [
            {
                "id": str(p.id),
                "name": p.name,
                "deal_type": p.deal_type_id,
                "deal_type_name": p.deal_type.name_fa,
                "versions": [
                    {
                        "id": str(v.id),
                        "version_number": v.version_number,
                        "formula_type": v.formula_type,
                        "gross_rate_percent": str(v.gross_rate_percent),
                        "fixed_amount": str(v.fixed_amount),
                        "tax_rate_percent": str(v.tax_rate_percent),
                        "agency_house_percent": str(v.agency_house_percent),
                        "primary_agent_percent": str(v.primary_agent_percent),
                        "co_agent_split_ratio": str(v.co_agent_split_ratio),
                        "is_published": v.is_published,
                    }
                    for v in p.versions.order_by("-version_number")
                ],
            }
            for p in list_commission_policies(ctx.agency_id)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/policies", status_code=201)
async def create_policy_endpoint(
    body: CommissionPolicyCreateBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.commissions.services import create_commission_policy

        p = create_commission_policy(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return {"id": str(p.id), "name": p.name}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/calculate", status_code=201)
async def calculate_commission_endpoint(
    body: CommissionCalculateBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.commissions.services import calculate_commission_for_deal_service

        dc = calculate_commission_for_deal_service(
            user=ctx.user,
            agency_id=ctx.agency_id,
            deal_id=body.deal_id,
            policy_version_id=body.policy_version_id,
            discount_amount=body.discount_amount,
        )
        return _ser_commission(dc)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/{commission_id}/status")
async def commission_status_endpoint(
    commission_id: UUID,
    body: CommissionStatusBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.commissions.services import update_commission_status

        dc = update_commission_status(
            user=ctx.user,
            agency_id=ctx.agency_id,
            commission_id=commission_id,
            status_value=body.status,
        )
        return {"id": str(dc.id), "status": dc.status}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))
