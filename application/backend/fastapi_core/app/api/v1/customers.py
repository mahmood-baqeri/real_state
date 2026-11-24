from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from django.db import models
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, require_agency_context
from app.schemas.common import ok

router = APIRouter(tags=["Customers & Leads"])


class CustomerCreateBody(BaseModel):
    customer_type: str = "BUYER"
    full_name: str
    primary_phone: str
    secondary_phone: str = ""
    email: str = ""
    source: str = "PORTAL"
    assigned_membership_id: Optional[UUID] = None
    lead_score: int = 50
    readiness_level: str = "MEDIUM"
    tags: list[str] = []


class CustomerPatchBody(BaseModel):
    customer_type: Optional[str] = None
    full_name: Optional[str] = None
    primary_phone: Optional[str] = None
    secondary_phone: Optional[str] = None
    email: Optional[str] = None
    source: Optional[str] = None
    assigned_membership_id: Optional[UUID] = None
    lead_score: Optional[int] = None
    readiness_level: Optional[str] = None
    is_active: Optional[bool] = None


class CustomerShareBody(BaseModel):
    membership_id: UUID
    access_level: str = "VIEW"
    expires_at: Optional[datetime] = None


class CustomerRequirementBody(BaseModel):
    deal_type_id: str
    property_type_id: str
    target_city: str = ""
    target_districts: list[str] = []
    min_area_sqm: Decimal = Decimal("0")
    max_area_sqm: Decimal = Decimal("99999")
    currency_id: str = "IRT"
    min_budget: Decimal = Decimal("0")
    max_budget: Decimal = Decimal("0")
    min_bedrooms: int = 0
    priority: str = "NORMAL"


class CustomerInteractionBody(BaseModel):
    channel: str = "NOTE"
    summary: str
    is_private: bool = False


class LeadCreateBody(BaseModel):
    full_name: str
    phone_number: str
    request_type: str = "BUY"
    property_id: Optional[UUID] = None
    assigned_membership_id: Optional[UUID] = None
    source: str = "PORTAL"
    notes: str = ""


class LeadPatchBody(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    request_type: Optional[str] = None
    property_id: Optional[UUID] = None
    assigned_membership_id: Optional[UUID] = None
    source: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class LeadActivityBody(BaseModel):
    activity_type: str = "NOTE"
    note: str


def _ser_customer(c) -> dict:
    return {
        "id": str(c.id),
        "agency": str(c.agency_id),
        "agency_name": c.agency.name if c.agency else None,
        "customer_type": c.customer_type,
        "full_name": c.full_name,
        "primary_phone": c.primary_phone,
        "secondary_phone": c.secondary_phone,
        "email": c.email,
        "source": c.source,
        "assigned_membership": str(c.assigned_membership_id) if c.assigned_membership_id else None,
        "assigned_agent_name": c.assigned_membership.user.full_name if c.assigned_membership else None,
        "lead_score": c.lead_score,
        "readiness_level": c.readiness_level,
        "tags": c.tags,
        "is_active": c.is_active,
        "shares": [
            {
                "id": str(s.id),
                "membership_id": str(s.membership_id),
                "agent_name": s.membership.user.full_name,
                "access_level": s.access_level,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            }
            for s in c.shares.filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now()))
        ],
        "requirements": [
            {
                "id": str(r.id),
                "deal_type": r.deal_type_id,
                "property_type": r.property_type_id,
                "target_city": r.target_city,
                "target_districts": r.target_districts,
                "min_area_sqm": str(r.min_area_sqm),
                "max_area_sqm": str(r.max_area_sqm),
                "min_budget": str(r.min_budget),
                "max_budget": str(r.max_budget),
                "min_bedrooms": r.min_bedrooms,
            }
            for r in c.requirements.all()
        ],
        "created_at": c.created_at.isoformat(),
    }


def _ser_lead(l) -> dict:
    return {
        "id": str(l.id),
        "agency_id": str(l.agency_id),
        "agency_name": l.agency.name if l.agency else None,
        "full_name": l.full_name,
        "phone_number": l.phone_number,
        "request_type": l.request_type,
        "property_id": str(l.property_id) if l.property_id else None,
        "property_title": l.property.title if l.property else None,
        "source": l.source,
        "assigned_membership_id": str(l.assigned_membership_id) if l.assigned_membership_id else None,
        "assigned_agent_name": l.assigned_membership.user.full_name if l.assigned_membership else None,
        "converted_customer_id": str(l.converted_customer_id) if l.converted_customer_id else None,
        "status": l.status,
        "notes": l.notes,
        "activities": [
            {
                "id": str(a.id),
                "activity_type": a.activity_type,
                "note": a.note,
                "created_by_name": a.created_by.full_name if a.created_by else "سیستم",
                "created_at": a.created_at.isoformat(),
            }
            for a in l.activities.all()
        ],
        "created_at": l.created_at.isoformat(),
    }


@router.get("/customers")
async def get_customers(
    q: Optional[str] = None,
    customer_type: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.customers.services import list_customers
        from common.pagination import paginate_queryset

        qs = list_customers(user=ctx.user, agency_id=ctx.agency_id, q=q, customer_type=customer_type)
        return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser_customer)

    items, meta = await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None)
    return ok(items, meta=meta)


@router.get("/customers/{customer_id}")
async def get_customer_detail_endpoint(
    customer_id: UUID,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.customers.services import get_customer_detail

        res = get_customer_detail(user=ctx.user, agency_id=ctx.agency_id, customer_id=customer_id)
        data = _ser_customer(res["customer"])
        data["interactions"] = [
            {
                "id": str(i.id),
                "channel": i.channel,
                "summary": i.summary,
                "is_private": i.is_private,
                "author_name": (
                    i.membership.user.full_name
                    if i.membership and i.membership.user
                    else (i.created_by.full_name if i.created_by else "سیستم")
                ),
                "created_at": i.created_at.isoformat(),
            }
            for i in res["interactions"]
        ]
        data["tasks"] = [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "due_at": t.due_at.isoformat(),
                "assigned_name": t.assigned_membership.user.full_name if t.assigned_membership else None,
            }
            for t in res["tasks"]
        ]
        data["contracts"] = [
            {
                "id": str(c.id),
                "contract_number": c.contract_number,
                "status": c.status,
                "amount": str(c.amount),
                "property_title": c.property.title if c.property else None,
                "created_at": c.created_at.isoformat(),
            }
            for c in res["contracts"]
        ]
        data["negotiations"] = [
            {
                "id": str(n.id),
                "status": n.status,
                "property_title": n.property.title if n.property else None,
                "latest_proposed_price": str(n.latest_proposed_price),
                "created_at": n.created_at.isoformat(),
            }
            for n in res["negotiations"]
        ]
        data["appointments"] = [
            {
                "id": str(a.id),
                "status": a.status,
                "property_title": a.property.title if a.property else None,
                "scheduled_start": a.scheduled_start.isoformat(),
            }
            for a in res["appointments"]
        ]
        data["documents"] = [
            {
                "id": str(d.id),
                "title": d.title,
                "category": d.category,
                "created_at": d.created_at.isoformat(),
            }
            for d in res["documents"]
        ]
        return data

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/customers", status_code=201)
async def post_customer(body: CustomerCreateBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.customers.services import create_customer

        c = create_customer(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return _ser_customer(c)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.patch("/customers/{customer_id}")
async def patch_customer(
    customer_id: UUID, body: CustomerPatchBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.customers.services import update_customer

        c = update_customer(
            user=ctx.user, agency_id=ctx.agency_id, customer_id=customer_id, data=body.model_dump(exclude_none=True)
        )
        return _ser_customer(c)

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.delete("/customers/{customer_id}")
async def delete_customer_endpoint(
    customer_id: UUID, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.customers.services import soft_delete_customer

        c = soft_delete_customer(user=ctx.user, agency_id=ctx.agency_id, customer_id=customer_id)
        return {"id": str(c.id), "archived": True}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/customers/{customer_id}/interactions", status_code=201)
async def post_customer_interaction(
    customer_id: UUID,
    body: CustomerInteractionBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.customers.services import add_customer_interaction

        item = add_customer_interaction(
            user=ctx.user,
            agency_id=ctx.agency_id,
            customer_id=customer_id,
            channel=body.channel,
            summary=body.summary,
            is_private=body.is_private,
        )
        return {
            "id": str(item.id),
            "channel": item.channel,
            "summary": item.summary,
            "created_at": item.created_at.isoformat(),
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/customers/{customer_id}/share")
async def post_customer_share(
    customer_id: UUID, body: CustomerShareBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.customers.services import share_customer

        s = share_customer(
            user=ctx.user,
            agency_id=ctx.agency_id,
            customer_id=customer_id,
            target_membership_id=body.membership_id,
            access_level=body.access_level,
            expires_at=body.expires_at,
        )
        return {"shared": True, "id": str(s.id)}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.delete("/customers/{customer_id}/share/{membership_id}")
async def delete_customer_share_endpoint(customer_id: UUID, membership_id: UUID, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.customers.services import revoke_customer_share
        revoked = revoke_customer_share(user=ctx.user, agency_id=ctx.agency_id, customer_id=customer_id, membership_id=membership_id)
        return {"revoked": revoked}
    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/customers/{customer_id}/requirements", status_code=201)
async def post_customer_req(
    customer_id: UUID, body: CustomerRequirementBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.customers.services import add_customer_requirement

        r = add_customer_requirement(
            user=ctx.user, agency_id=ctx.agency_id, customer_id=customer_id, data=body.model_dump()
        )
        return {"id": str(r.id), "target_city": r.target_city}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.get("/leads")
async def get_leads(
    status: Optional[str] = None,
    assigned_membership_id: Optional[UUID] = None,
    q: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.customers.services import list_leads
        from common.pagination import paginate_queryset

        qs = list_leads(
            user=ctx.user,
            agency_id=ctx.agency_id,
            status_filter=status,
            assigned_membership_id=assigned_membership_id,
            q=q,
        )
        return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser_lead)

    items, meta = await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None)
    return ok(items, meta=meta)


@router.post("/leads", status_code=201)
async def post_lead(body: LeadCreateBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.customers.services import create_lead

        return _ser_lead(create_lead(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump()))

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.patch("/leads/{lead_id}")
async def patch_lead(lead_id: UUID, body: LeadPatchBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.customers.services import update_lead

        return _ser_lead(
            update_lead(
                user=ctx.user,
                agency_id=ctx.agency_id,
                lead_id=lead_id,
                data=body.model_dump(exclude_none=True),
            )
        )

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/leads/{lead_id}/activities", status_code=201)
async def post_lead_activity(
    lead_id: UUID,
    body: LeadActivityBody,
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.customers.services import add_lead_activity

        act = add_lead_activity(
            user=ctx.user,
            agency_id=ctx.agency_id,
            lead_id=lead_id,
            activity_type=body.activity_type,
            note=body.note,
        )
        return {
            "id": str(act.id),
            "activity_type": act.activity_type,
            "note": act.note,
            "created_by_name": act.created_by.full_name if act.created_by else "سیستم",
            "created_at": act.created_at.isoformat(),
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.delete("/leads/{lead_id}")
async def delete_lead_endpoint(lead_id: UUID, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.customers.services import soft_delete_lead

        l = soft_delete_lead(user=ctx.user, agency_id=ctx.agency_id, lead_id=lead_id)
        return {"id": str(l.id), "archived": True}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


@router.post("/leads/{lead_id}/convert")
async def convert_lead(lead_id: UUID, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.customers.services import convert_lead_to_customer

        lead, cust = convert_lead_to_customer(user=ctx.user, agency_id=ctx.agency_id, lead_id=lead_id)
        return {"lead": _ser_lead(lead), "customer_id": str(cust.id)}

    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))


class CustomerTransferBody(BaseModel):
    target_membership_id: UUID
    reason: str


class CustomerMergeBody(BaseModel):
    primary_customer_id: UUID
    duplicate_customer_id: UUID


class FollowUpTaskCreateBody(BaseModel):
    assigned_membership_id: UUID
    title: str
    due_at: datetime


class FollowUpTaskStatusBody(BaseModel):
    status: str


@router.get("/customers/{customer_id}/timeline")
async def customer_timeline_endpoint(
    customer_id: UUID, limit: int = Query(default=100, ge=1, le=300),
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.customers.services import customer_timeline
        return customer_timeline(user=ctx.user, agency_id=ctx.agency_id, customer_id=customer_id, limit=limit)
    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))



@router.get("/customers/{customer_id}/duplicates")
async def customer_duplicates_endpoint(customer_id: UUID, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.customers.services import find_customer_duplicates
        matches = find_customer_duplicates(user=ctx.user, agency_id=ctx.agency_id, customer_id=customer_id)
        return [{"customer": _ser_customer(m["customer"]), "match_reasons": m["match_reasons"], "confidence": m["confidence"]} for m in matches]
    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))



@router.post("/customers/merge")
async def merge_customers_endpoint(body: CustomerMergeBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.customers.services import merge_customers
        customer = merge_customers(user=ctx.user, agency_id=ctx.agency_id, primary_id=body.primary_customer_id, duplicate_id=body.duplicate_customer_id)
        return {"canonical_customer": _ser_customer(customer), "merged": True}
    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))



@router.post("/customers/{customer_id}/transfer")
async def transfer_customer_endpoint(customer_id: UUID, body: CustomerTransferBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.customers.services import transfer_customer
        customer = transfer_customer(user=ctx.user, agency_id=ctx.agency_id, customer_id=customer_id, target_membership_id=body.target_membership_id, reason=body.reason)
        return {"customer_id": str(customer.id), "assigned_membership_id": str(customer.assigned_membership_id), "transferred": True}
    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))



@router.post("/customers/{customer_id}/tasks", status_code=201)
async def create_customer_task_endpoint(customer_id: UUID, body: FollowUpTaskCreateBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.customers.services import create_follow_up_task
        task = create_follow_up_task(user=ctx.user, agency_id=ctx.agency_id, customer_id=customer_id, assigned_membership_id=body.assigned_membership_id, title=body.title, due_at=body.due_at)
        return {"id": str(task.id), "title": task.title, "status": task.status, "due_at": task.due_at.isoformat(), "assigned_membership_id": str(task.assigned_membership_id)}
    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))



@router.patch("/customer-tasks/{task_id}/status")
async def update_customer_task_status_endpoint(task_id: UUID, body: FollowUpTaskStatusBody, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.customers.services import update_follow_up_task
        task = update_follow_up_task(user=ctx.user, agency_id=ctx.agency_id, task_id=task_id, status_value=body.status)
        return {"id": str(task.id), "status": task.status, "completed_at": task.completed_at.isoformat() if task.completed_at else None}
    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))
