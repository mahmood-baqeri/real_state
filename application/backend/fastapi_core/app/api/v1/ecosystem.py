from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from django.db import transaction
from django.db.models import Avg, Count, Min, Max, Q
from django.utils import timezone

from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, require_agency_context
from app.schemas.common import ok

router = APIRouter(prefix="/ecosystem", tags=["Ecosystem & Market"])

# Explicit transition graph. Terminal states cannot be silently reopened.
CASE_TRANSITIONS = {
    "OPEN": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"WAITING", "RESOLVED", "CANCELLED"},
    "WAITING": {"IN_PROGRESS", "RESOLVED", "CANCELLED"},
    "RESOLVED": set(),
    "CANCELLED": set(),
}


class CaseCreate(BaseModel):
    customer_id: UUID
    contract_id: Optional[UUID] = None
    title: str = Field(min_length=2, max_length=180)
    description: str = Field(default="", max_length=10000)
    category: str = Field(default="GENERAL", min_length=2, max_length=40)
    priority: str = "MEDIUM"
    due_at: Optional[datetime] = None
    assigned_membership_id: Optional[UUID] = None


class CasePatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=180)
    description: Optional[str] = Field(default=None, max_length=10000)
    category: Optional[str] = Field(default=None, min_length=2, max_length=40)
    priority: Optional[str] = None
    status: Optional[str] = None
    due_at: Optional[datetime] = None
    assigned_membership_id: Optional[UUID] = None
    update_note: str = Field(default="", max_length=2000)


class PropertyShareCreate(BaseModel):
    property_id: UUID


class SettlementCreate(BaseModel):
    payer_agency_id: UUID
    payee_agency_id: UUID
    amount: Decimal = Field(gt=0, max_digits=20, decimal_places=2)
    currency_code: str = Field(min_length=3, max_length=10)
    split_percent: Decimal = Field(ge=0, le=100, max_digits=6, decimal_places=2)
    contract_id: Optional[UUID] = None
    description: str = Field(default="", max_length=300)


class SettlementTransition(BaseModel):
    status: str
    external_reference: str = Field(default="", max_length=120)


def _require_member(user, agency_id, permission=None):
    from common.permissions import get_active_membership, has_agency_permission, is_super_admin
    if is_super_admin(user):
        return None
    membership = get_active_membership(user, agency_id)
    if not membership:
        raise HTTPException(403, "عضویت فعال در این آژانس الزامی است.")
    if permission and not has_agency_permission(user, agency_id, permission):
        raise HTTPException(403, "مجوز لازم برای این عملیات را ندارید.")
    return membership


def _customer_access(user, customer, write=False):
    from common.permissions import can_edit_customer, get_active_membership, is_super_admin
    from apps.customers.models import CustomerShare
    if is_super_admin(user):
        return True
    membership = get_active_membership(user, customer.agency_id)
    if not membership:
        return False
    if membership.role.code == "AGENCY_MANAGER":
        return True
    if write:
        return can_edit_customer(user, customer)
    if customer.assigned_membership_id == membership.id:
        return True
    return CustomerShare.objects.filter(
        customer=customer, membership=membership
    ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())).exists()


def _case_data(c):
    return {
        "id": str(c.id), "customer_id": str(c.customer_id),
        "customer_name": c.customer.full_name,
        "contract_id": str(c.contract_id) if c.contract_id else None,
        "title": c.title, "description": c.description, "category": c.category,
        "status": c.status, "priority": c.priority,
        "due_at": c.due_at.isoformat() if c.due_at else None,
        "assigned_membership_id": str(c.assigned_membership_id) if c.assigned_membership_id else None,
        "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
        "updates": [
            {"id": str(u.id), "body": u.body, "status_from": u.status_from,
             "status_to": u.status_to, "created_at": u.created_at.isoformat()}
            for u in c.updates.all()
        ],
        "created_at": c.created_at.isoformat(),
    }


@router.get("/after-deal/cases")
async def list_after_deal_cases(
    status: Optional[str] = None, page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: RequestContext = Depends(require_agency_context),
):
    def op():
        from apps.ecosystem.models import AfterDealCase
        from apps.accounts.models import AgencyMembership
        from common.permissions import is_super_admin
        qs = AfterDealCase.objects.filter(agency_id=ctx.agency_id).select_related(
            "customer", "assigned_membership"
        ).prefetch_related("updates")
        if status:
            if status not in AfterDealCase.Status.values:
                raise HTTPException(400, "وضعیت فیلتر نامعتبر است.")
            qs = qs.filter(status=status)
        if not is_super_admin(ctx.user):
            membership = AgencyMembership.objects.filter(
                user=ctx.user, agency_id=ctx.agency_id, status="ACTIVE"
            ).select_related("role").first()
            if not membership:
                raise HTTPException(403, "عضویت فعال یافت نشد.")
            if membership.role.code != "AGENCY_MANAGER":
                from apps.customers.models import CustomerShare
                accessible_customer_ids = CustomerShare.objects.filter(
                    membership=membership
                ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())).values("customer_id")
                qs = qs.filter(
                    Q(customer__assigned_membership=membership) |
                    Q(customer_id__in=accessible_customer_ids) |
                    Q(assigned_membership=membership)
                ).distinct()
        total = qs.count()
        rows = qs.order_by("-created_at")[(page-1)*page_size:page*page_size]
        return {"items": [_case_data(x) for x in rows],
                "meta": {"page": page, "page_size": page_size, "total": total}}
    result = await run_django(op, agency_id=ctx.agency_id, user_id=ctx.user.id)
    return ok(result["items"], meta=result["meta"])


@router.post("/after-deal/cases", status_code=201)
async def create_after_deal_case(body: CaseCreate, ctx: RequestContext = Depends(require_agency_context)):
    def op():
        from apps.ecosystem.models import AfterDealCase, AfterDealUpdate
        from apps.customers.models import Customer
        from apps.accounts.models import AgencyMembership
        from apps.contracts.models import Contract, ContractParty
        from apps.audit.services import record_audit_event

        customer = Customer.objects.filter(
            id=body.customer_id, agency_id=ctx.agency_id, is_deleted=False, is_active=True
        ).first()
        if not customer or not _customer_access(ctx.user, customer, write=True):
            raise HTTPException(404, "مشتری در محدوده دسترسی شما یافت نشد.")
        if body.priority not in AfterDealCase.Priority.values:
            raise HTTPException(400, "اولویت نامعتبر است.")
        membership = None
        if body.assigned_membership_id:
            membership = AgencyMembership.objects.filter(
                id=body.assigned_membership_id, agency_id=ctx.agency_id,
                status=AgencyMembership.Status.ACTIVE
            ).first()
            if not membership:
                raise HTTPException(400, "عضو انتخاب‌شده معتبر نیست.")
        contract_id = body.contract_id
        if contract_id:
            contract = Contract.objects.filter(
                id=contract_id, agency_id=ctx.agency_id,
                status__in=["SIGNED", "ACTIVE", "COMPLETED"]
            ).first()
            if not contract or not ContractParty.objects.filter(
                contract=contract, customer_id=customer.id, party_role="OWNER"
            ).exists():
                raise HTTPException(400, "قرارداد معتبر و مرتبط با مالک این پرونده نیست.")
        c = AfterDealCase.objects.create(
            agency_id=ctx.agency_id, customer=customer, contract_id=contract_id,
            title=body.title.strip(), description=body.description.strip(),
            category=body.category.strip().upper(), priority=body.priority,
            due_at=body.due_at, assigned_membership=membership, created_by=ctx.user
        )
        AfterDealUpdate.objects.create(
            case=c, body="پرونده خدمات پس از معامله ایجاد شد.", created_by=ctx.user
        )
        record_audit_event(
            action="AFTER_DEAL_CASE_CREATED", resource_type="AfterDealCase",
            resource_id=str(c.id), actor=ctx.user, agency_id=ctx.agency_id,
            after_state={"customer_id": str(customer.id), "contract_id": str(contract_id) if contract_id else None}
        )
        c = AfterDealCase.objects.select_related("customer").prefetch_related("updates").get(id=c.id)
        return _case_data(c)
    return ok(await run_django(op, agency_id=ctx.agency_id, user_id=ctx.user.id))


@router.patch("/after-deal/cases/{case_id}")
async def update_after_deal_case(
    case_id: UUID, body: CasePatch, ctx: RequestContext = Depends(require_agency_context)
):
    def op():
        from apps.ecosystem.models import AfterDealCase, AfterDealUpdate
        from apps.accounts.models import AgencyMembership
        from apps.audit.services import record_audit_event

        c = AfterDealCase.objects.select_for_update().filter(
            id=case_id, agency_id=ctx.agency_id
        ).select_related("customer").first()
        if not c:
            raise HTTPException(404, "پرونده خدمات یافت نشد.")
        if not _customer_access(ctx.user, c.customer, write=True):
            raise HTTPException(403, "دسترسی ویرایش این پرونده را ندارید.")
        data = body.model_dump(exclude_unset=True)
        note = data.pop("update_note", "")
        new_status = data.get("status")
        if new_status is not None:
            if new_status not in AfterDealCase.Status.values:
                raise HTTPException(400, "وضعیت نامعتبر است.")
            if new_status != c.status and new_status not in CASE_TRANSITIONS.get(c.status, set()):
                raise HTTPException(409, f"انتقال وضعیت از {c.status} به {new_status} مجاز نیست.")
        if "priority" in data and data["priority"] not in AfterDealCase.Priority.values:
            raise HTTPException(400, "اولویت نامعتبر است.")
        if "category" in data:
            data["category"] = data["category"].strip().upper()
        if "title" in data:
            data["title"] = data["title"].strip()
        if "description" in data:
            data["description"] = data["description"].strip()
        if "assigned_membership_id" in data:
            mid = data.pop("assigned_membership_id")
            membership = AgencyMembership.objects.filter(
                id=mid, agency_id=ctx.agency_id, status=AgencyMembership.Status.ACTIVE
            ).first() if mid else None
            if mid and not membership:
                raise HTTPException(400, "عضو انتخاب‌شده معتبر نیست.")
            c.assigned_membership = membership
        old_status = c.status
        old = {"status": old_status, "priority": c.priority, "assigned_membership_id": str(c.assigned_membership_id) if c.assigned_membership_id else None}
        for key, value in data.items():
            setattr(c, key, value)
        if c.status == AfterDealCase.Status.RESOLVED:
            c.resolved_at = c.resolved_at or timezone.now()
        else:
            c.resolved_at = None
        c.updated_by = ctx.user
        c.save()
        if note or old_status != c.status:
            AfterDealUpdate.objects.create(
                case=c, body=note or "وضعیت پرونده تغییر کرد.",
                status_from=old_status, status_to=c.status, created_by=ctx.user
            )
        record_audit_event(
            action="AFTER_DEAL_CASE_UPDATED", resource_type="AfterDealCase",
            resource_id=str(c.id), actor=ctx.user, agency_id=ctx.agency_id,
            before_state=old, after_state={"status": c.status, "priority": c.priority,
                "assigned_membership_id": str(c.assigned_membership_id) if c.assigned_membership_id else None}
        )
        c = AfterDealCase.objects.select_related("customer").prefetch_related("updates").get(id=c.id)
        return _case_data(c)
    return ok(await run_django(op, agency_id=ctx.agency_id, user_id=ctx.user.id))


def _trust_score_payload(agency_id):
    from apps.agencies.models import Agency, AgencyCooperation
    from apps.ecosystem.models import AfterDealCase
    agency = Agency.objects.get(id=agency_id)
    cases = AfterDealCase.objects.filter(agency_id=agency_id)
    total = cases.count()
    resolved = cases.filter(status="RESOLVED").count()
    overdue = cases.filter(due_at__lt=timezone.now()).exclude(
        status__in=["RESOLVED", "CANCELLED"]
    ).count()
    partners = AgencyCooperation.objects.filter(
        Q(requester_agency_id=agency_id) | Q(provider_agency_id=agency_id),
        status="ACTIVE"
    ).count()
    status_base = 65 if agency.status in ["ACTIVE", "APPROVED"] else 25
    resolution_rate = (resolved / total) if total else None
    overdue_rate = (overdue / total) if total else None
    resolution_points = round((resolution_rate or 0) * 25)
    overdue_penalty = round((overdue_rate or 0) * 20)
    partner_points = min(partners * 2, 10)
    score = max(0, min(100, status_base + resolution_points - overdue_penalty + partner_points))
    return {
        "agency_id": str(agency_id), "score": score,
        "label": "شاخص داخلی و آزمایشی؛ نه رتبه‌بندی عمومی یا اعتبارسنجی مستقل",
        "methodology_version": "legacy-compatible-1.1",
        "methodology": "پایه وضعیت آژانس ۲۵ یا ۶۵ امتیاز؛ نرخ حل پرونده × ۲۵؛ کسر نرخ پرونده معوق × ۲۰؛ همکاری فعال هر مورد ۲ امتیاز تا سقف ۱۰. وزن‌ها نیازمند تصویب کسب‌وکار هستند.",
        "components": {
            "agency_status": {"points": status_base, "max_points": 65, "evidence": agency.status},
            "case_resolution": {"points": resolution_points, "max_points": 25, "rate": round(resolution_rate * 100, 2) if resolution_rate is not None else None},
            "overdue_cases": {"points": -overdue_penalty, "max_penalty": 20, "rate": round(overdue_rate * 100, 2) if overdue_rate is not None else None},
            "active_cooperation": {"points": partner_points, "max_points": 10, "count": partners},
        },
        "metrics": {"after_deal_cases": total, "resolved_cases": resolved,
                    "overdue_cases": overdue, "active_partners": partners},
        "limitations": ["تعداد و کیفیت داده در امتیاز لحاظ نشده است.",
                        "تأیید مستقل اطلاعات و رضایت انتشار عمومی پیاده‌سازی نشده است.",
                        "این شاخص نباید مبنای تصمیم مالی یا رتبه‌بندی عمومی قرار گیرد."]
    }


@router.get("/trust-score")
async def agency_trust_score(ctx: RequestContext = Depends(require_agency_context)):
    def op():
        _require_member(ctx.user, ctx.agency_id)
        return _trust_score_payload(ctx.agency_id)
    return ok(await run_django(op, agency_id=ctx.agency_id, user_id=ctx.user.id))


@router.post("/trust-score/snapshots", status_code=201)
async def create_trust_score_snapshot(ctx: RequestContext = Depends(require_agency_context)):
    def op():
        from apps.ecosystem.models import TrustScoreSnapshot
        from apps.audit.services import record_audit_event
        _require_member(ctx.user, ctx.agency_id, "agency.manage_policy")
        payload = _trust_score_payload(ctx.agency_id)
        snap = TrustScoreSnapshot.objects.create(
            agency_id=ctx.agency_id, score=payload["score"],
            methodology_version=payload["methodology_version"],
            components=payload["components"], evidence=payload["metrics"],
            coverage=100 if payload["metrics"]["after_deal_cases"] else 50,
            is_public=False, created_by=ctx.user
        )
        record_audit_event(
            action="TRUST_SCORE_SNAPSHOT_CREATED", resource_type="TrustScoreSnapshot",
            resource_id=str(snap.id), actor=ctx.user, agency_id=ctx.agency_id,
            after_state={"score": snap.score, "methodology_version": snap.methodology_version}
        )
        return {"id": str(snap.id), "score": snap.score, "created_at": snap.created_at.isoformat(),
                "is_public": False, "components": snap.components}
    return ok(await run_django(op, agency_id=ctx.agency_id, user_id=ctx.user.id))


@router.get("/market/summary")
async def ecosystem_market_summary(
    city: str = Query("تهران", min_length=2, max_length=80),
    ctx: RequestContext = Depends(require_agency_context)
):
    def op():
        from apps.properties.models import Property
        from apps.agencies.models import Agency
        agency = Agency.objects.only("default_currency_id").get(id=ctx.agency_id)
        qs = Property.objects.filter(
            agency_id=ctx.agency_id, is_deleted=False,
            status=Property.Status.PUBLISHED,
            visibility=Property.Visibility.PUBLIC_PORTAL,
            location__city=city,
            currency_id=agency.default_currency_id,
        )
        agg = qs.aggregate(
            count=Count("id"), avg_price=Avg("total_price"),
            min_price=Min("total_price"), max_price=Max("total_price"),
            avg_area=Avg("built_area_sqm"), avg_ppsqm=Avg("price_per_sqm")
        )
        return {
            "city": city, "currency": agency.default_currency_id, "inventory_count": agg["count"] or 0,
            "average_price": str(agg["avg_price"]) if agg["avg_price"] is not None else None,
            "minimum_price": str(agg["min_price"]) if agg["min_price"] is not None else None,
            "maximum_price": str(agg["max_price"]) if agg["max_price"] is not None else None,
            "average_area_sqm": str(agg["avg_area"]) if agg["avg_area"] is not None else None,
            "average_price_per_sqm": str(agg["avg_ppsqm"]) if agg["avg_ppsqm"] is not None else None,
            "scope": "فقط آگهی‌های منتشرشده عمومی همین آژانس؛ نه کل بازار شهر"
        }
    return ok(await run_django(op, agency_id=ctx.agency_id, user_id=ctx.user.id))


@router.get("/market/radar")
async def market_opportunity_radar(
    city: Optional[str] = Query(None, max_length=80),
    stale_days: int = Query(30, ge=7, le=365),
    ctx: RequestContext = Depends(require_agency_context)
):
    def op():
        from apps.properties.models import Property
        from common.permissions import can_view_property
        qs = Property.objects.filter(
            agency_id=ctx.agency_id, is_deleted=False,
            status=Property.Status.PUBLISHED
        ).select_related("location", "verification", "property_type", "deal_type")
        if city:
            qs = qs.filter(location__city=city)
        qs = qs.order_by("-inquiry_count", "-view_count")[:500]
        cutoff = timezone.now() - timedelta(days=stale_days)
        items = []
        for p in qs:
            if not can_view_property(ctx.user, p):
                continue
            signals = []
            if p.price_valid_until and p.price_valid_until < timezone.now():
                signals.append({"code": "PRICE_REVIEW", "label": "اعتبار قیمت منقضی شده"})
            if p.created_at < cutoff and p.inquiry_count == 0:
                signals.append({"code": "LOW_CONVERSION", "label": "بازدید بدون درخواست"})
            if p.inquiry_count >= 3:
                signals.append({"code": "HIGH_DEMAND", "label": "تقاضای ثبت‌شده بالا"})
            verification = getattr(p, "verification", None)
            if not verification or verification.verification_status != "VERIFIED":
                signals.append({"code": "VERIFY_REQUIRED", "label": "اعتبارسنجی کامل نشده"})
            if signals:
                items.append({
                    "property_id": str(p.id), "title": p.title,
                    "city": getattr(p, "location", None).city if getattr(p, "location", None) else "",
                    "price": str(p.total_price), "currency": p.currency_id,
                    "views": p.view_count, "inquiries": p.inquiry_count,
                    "signals": signals,
                    "suggested_actions": sorted({s["code"] for s in signals}),
                })
        return {"items": items[:100], "meta": {"total": len(items), "stale_days": stale_days,
                "scope": "فقط فایل‌های قابل مشاهده همین آژانس؛ سیگنال عملیاتی است و پیش‌بینی سود نیست."}}
    result = await run_django(op, agency_id=ctx.agency_id, user_id=ctx.user.id)
    return ok(result["items"], meta=result["meta"])


@router.get("/market/competitors")
async def competitor_market_benchmark(
    city: str = Query(..., min_length=2, max_length=80),
    min_sample: int = Query(5, ge=5, le=100),
    ctx: RequestContext = Depends(require_agency_context)
):
    def op():
        from apps.properties.models import Property
        from apps.agencies.models import Agency
        agency = Agency.objects.only("default_currency_id").get(id=ctx.agency_id)
        currency_code = agency.default_currency_id
        qs = Property.objects.all_tenants().filter(
            is_deleted=False, status=Property.Status.PUBLISHED,
            visibility=Property.Visibility.PUBLIC_PORTAL,
            location__city=city, currency_id=currency_code,
        ).exclude(agency_id=ctx.agency_id)
        agg = qs.aggregate(
            count=Count("id"), avg_price=Avg("total_price"),
            min_price=Min("total_price"), max_price=Max("total_price"),
            avg_price_per_sqm=Avg("price_per_sqm"), avg_area=Avg("built_area_sqm")
        )
        count = agg["count"] or 0
        if count < min_sample:
            return {"city": city, "currency": currency_code, "sample_size": count, "minimum_sample": min_sample,
                    "available": False, "message": "تعداد آگهی عمومی مستقل برای ارائه آمار تجمیعی کافی نیست.",
                    "competitor_agencies": None, "average_price": None,
                    "average_price_per_sqm": None, "average_area_sqm": None}
        return {
            "city": city, "currency": currency_code, "sample_size": count, "minimum_sample": min_sample,
            "available": True, "competitor_agencies": None,
            "average_price": str(agg["avg_price"]) if agg["avg_price"] is not None else None,
            "minimum_price": str(agg["min_price"]) if agg["min_price"] is not None else None,
            "maximum_price": str(agg["max_price"]) if agg["max_price"] is not None else None,
            "average_price_per_sqm": str(agg["avg_price_per_sqm"]) if agg["avg_price_per_sqm"] is not None else None,
            "average_area_sqm": str(agg["avg_area"]) if agg["avg_area"] is not None else None,
            "scope": "تجمیع آگهی‌های عمومی منتشرشده سایر آژانس‌ها؛ بدون نام آژانس یا داده مالک"
        }
    return ok(await run_django(op, agency_id=ctx.agency_id, user_id=ctx.user.id))


@router.get("/owners/{owner_customer_id}/report")
async def owner_report(
    owner_customer_id: UUID,
    period_start: date = Query(...),
    period_end: date = Query(...),
    ctx: RequestContext = Depends(require_agency_context)
):
    if period_end < period_start or (period_end - period_start).days > 366:
        raise HTTPException(422, "بازه گزارش باید معتبر و حداکثر ۳۶۶ روز باشد.")
    def op():
        from apps.customers.models import Customer
        from apps.properties.models import PropertyOwner, PropertyPriceHistory
        from apps.ecosystem.models import OwnerReportSnapshot
        from common.permissions import can_view_property
        from apps.audit.services import record_audit_event
        owner = Customer.objects.filter(
            id=owner_customer_id, agency_id=ctx.agency_id, is_deleted=False,
            customer_type__in=["OWNER", "SELLER", "LANDLORD"]
        ).first()
        if not owner or not _customer_access(ctx.user, owner, write=False):
            raise HTTPException(404, "پرونده مالک در محدوده دسترسی شما یافت نشد.")
        links = PropertyOwner.objects.filter(
            owner_customer=owner, property__agency_id=ctx.agency_id,
            property__is_deleted=False
        ).select_related("property", "property__location")
        properties = [x.property for x in links if can_view_property(ctx.user, x.property)]
        if not properties:
            raise HTTPException(404, "ملک قابل مشاهده‌ای برای این مالک یافت نشد.")
        property_ids = [p.id for p in properties]
        changes = PropertyPriceHistory.objects.filter(
            property_id__in=property_ids, changed_at__date__gte=period_start,
            changed_at__date__lte=period_end
        ).count()
        data = {
            "owner_customer_id": str(owner.id), "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(), "property_count": len(properties),
            "properties": [{
                "property_id": str(p.id), "title": p.title,
                "city": getattr(p, "location", None).city if getattr(p, "location", None) else "",
                "status": p.status, "price": str(p.total_price),
                "currency": p.currency_id, "views": p.view_count,
                "inquiries": p.inquiry_count
            } for p in properties],
            "totals": {
                "views": sum(p.view_count for p in properties),
                "inquiries": sum(p.inquiry_count for p in properties),
                "price_changes_in_period": changes
            },
            "limitations": ["آمار بازدید و درخواست از شمارنده فعلی ملک خوانده می‌شود و ممکن است تاریخی نباشد.",
                            "گزارش مالی یا ارزش‌گذاری رسمی ملک محسوب نمی‌شود."]
        }
        snap, _ = OwnerReportSnapshot.objects.update_or_create(
            agency_id=ctx.agency_id, owner_customer=owner,
            period_start=period_start, period_end=period_end,
            defaults={"report_data": data, "generated_at": timezone.now(), "generated_by": ctx.user,
                      "updated_by": ctx.user}
        )
        record_audit_event(
            action="OWNER_REPORT_GENERATED", resource_type="OwnerReportSnapshot",
            resource_id=str(snap.id), actor=ctx.user, agency_id=ctx.agency_id,
            metadata={"owner_customer_id": str(owner.id), "period_start": period_start.isoformat(),
                      "period_end": period_end.isoformat(), "property_count": len(properties)}
        )
        return {"id": str(snap.id), **data, "generated_at": snap.generated_at.isoformat()}
    return ok(await run_django(op, agency_id=ctx.agency_id, user_id=ctx.user.id))


@router.post("/cooperations/{cooperation_id}/properties", status_code=201)
async def share_cooperation_property(
    cooperation_id: UUID, body: PropertyShareCreate,
    ctx: RequestContext = Depends(require_agency_context)
):
    def op():
        from apps.agencies.models import AgencyCooperation
        from apps.properties.models import Property
        from apps.ecosystem.models import CooperationPropertyShare
        from apps.audit.services import record_audit_event
        coop = AgencyCooperation.objects.filter(
            id=cooperation_id, status="ACTIVE"
        ).first()
        if not coop:
            raise HTTPException(404, "همکاری فعال یافت نشد.")
        if ctx.agency_id != coop.provider_agency_id:
            raise HTTPException(403, "فقط آژانس مالک فایل می‌تواند رضایت اشتراک را ثبت کند.")
        _require_member(ctx.user, coop.provider_agency_id, "agency.manage_policy")
        prop = Property.objects.filter(
            id=body.property_id, agency_id=coop.provider_agency_id,
            is_deleted=False, status="PUBLISHED",
            visibility__in=["MLS_SHARED", "PUBLIC_PORTAL"]
        ).first()
        if not prop:
            raise HTTPException(404, "فایل منتشرشده و مجاز برای اشتراک یافت نشد.")
        share, created = CooperationPropertyShare.objects.update_or_create(
            cooperation=coop, property=prop,
            defaults={"is_active": True, "consented_at": timezone.now(),
                      "revoked_at": None, "shared_by": ctx.user, "updated_by": ctx.user,
                      "created_by": ctx.user}
        )
        record_audit_event(
            action="COOPERATION_PROPERTY_SHARED", resource_type="CooperationPropertyShare",
            resource_id=str(share.id), actor=ctx.user, agency_id=ctx.agency_id,
            after_state={"cooperation_id": str(coop.id), "property_id": str(prop.id), "active": True}
        )
        return {"id": str(share.id), "property_id": str(prop.id), "active": True,
                "created": created, "consented_at": share.consented_at.isoformat()}
    return ok(await run_django(op, agency_id=ctx.agency_id, user_id=ctx.user.id))


@router.get("/cooperations/{cooperation_id}/properties")
async def list_cooperation_properties(
    cooperation_id: UUID, ctx: RequestContext = Depends(require_agency_context)
):
    def op():
        from apps.agencies.models import AgencyCooperation
        from apps.ecosystem.models import CooperationPropertyShare
        coop = AgencyCooperation.objects.filter(id=cooperation_id, status="ACTIVE").first()
        if not coop or ctx.agency_id not in [coop.requester_agency_id, coop.provider_agency_id]:
            raise HTTPException(404, "همکاری فعال یافت نشد.")
        _require_member(ctx.user, ctx.agency_id)
        shares = CooperationPropertyShare.objects.filter(
            cooperation=coop, is_active=True,
            property__agency_id=coop.provider_agency_id,
            property__status="PUBLISHED", property__is_deleted=False
        ).select_related("property", "property__location", "property__property_type", "property__deal_type")
        return [{
            "share_id": str(s.id), "property_id": str(s.property_id),
            "title": s.property.title, "description": s.property.description[:500],
            "property_type": s.property.property_type.name_fa,
            "deal_type": s.property.deal_type.name_fa,
            "city": getattr(s.property, "location", None).city if getattr(s.property, "location", None) else "",
            "area_sqm": str(s.property.built_area_sqm),
            "price": str(s.property.total_price), "currency": s.property.currency_id,
            "consented_at": s.consented_at.isoformat()
        } for s in shares]
    return ok(await run_django(op, agency_id=ctx.agency_id, user_id=ctx.user.id))


@router.delete("/cooperations/{cooperation_id}/properties/{share_id}")
async def revoke_cooperation_property_share(
    cooperation_id: UUID, share_id: UUID, ctx: RequestContext = Depends(require_agency_context)
):
    def op():
        from apps.agencies.models import AgencyCooperation
        from apps.ecosystem.models import CooperationPropertyShare
        from apps.audit.services import record_audit_event
        coop = AgencyCooperation.objects.filter(id=cooperation_id).first()
        if not coop or ctx.agency_id != coop.provider_agency_id:
            raise HTTPException(404, "همکاری یافت نشد.")
        _require_member(ctx.user, coop.provider_agency_id, "agency.manage_policy")
        share = CooperationPropertyShare.objects.select_for_update().filter(
            id=share_id, cooperation=coop, is_active=True
        ).first()
        if not share:
            raise HTTPException(404, "اشتراک فعال یافت نشد.")
        share.is_active = False
        share.revoked_at = timezone.now()
        share.updated_by = ctx.user
        share.save(update_fields=["is_active", "revoked_at", "updated_by", "updated_at"])
        record_audit_event(
            action="COOPERATION_PROPERTY_SHARE_REVOKED", resource_type="CooperationPropertyShare",
            resource_id=str(share.id), actor=ctx.user, agency_id=ctx.agency_id,
            after_state={"active": False}
        )
        return {"id": str(share.id), "active": False, "revoked_at": share.revoked_at.isoformat()}
    return ok(await run_django(op, agency_id=ctx.agency_id, user_id=ctx.user.id))


@router.post("/cooperations/{cooperation_id}/settlements", status_code=201)
async def create_cooperation_settlement(
    cooperation_id: UUID, body: SettlementCreate,
    ctx: RequestContext = Depends(require_agency_context)
):
    def op():
        from apps.agencies.models import AgencyCooperation
        from apps.contracts.models import Contract
        from apps.ecosystem.models import CooperationSettlement
        from apps.audit.services import record_audit_event
        coop = AgencyCooperation.objects.filter(id=cooperation_id, status="ACTIVE").first()
        if not coop or ctx.agency_id not in [coop.requester_agency_id, coop.provider_agency_id]:
            raise HTTPException(404, "همکاری فعال یافت نشد.")
        _require_member(ctx.user, ctx.agency_id, "agency.manage_policy")
        pair = {coop.requester_agency_id, coop.provider_agency_id}
        if body.payer_agency_id == body.payee_agency_id or {body.payer_agency_id, body.payee_agency_id} != pair:
            raise HTTPException(400, "پرداخت‌کننده و دریافت‌کننده باید دو آژانس همین همکاری باشند.")
        if body.currency_code.upper() not in ["IRT", "IRR", "USD", "EUR", "AED"]:
            raise HTTPException(400, "کد ارز پشتیبانی‌نشده است.")
        contract = None
        if body.contract_id:
            contract = Contract.objects.filter(
                id=body.contract_id, agency_id__in=pair,
                status__in=["SIGNED", "ACTIVE", "COMPLETED"]
            ).first()
            if not contract:
                raise HTTPException(400, "قرارداد مرتبط و معتبر یافت نشد.")
        settlement = CooperationSettlement.objects.create(
            cooperation=coop, contract=contract, payer_agency_id=body.payer_agency_id,
            payee_agency_id=body.payee_agency_id, amount=body.amount,
            currency_code=body.currency_code.upper(), split_percent=body.split_percent,
            description=body.description.strip(), status="DRAFT", created_by=ctx.user
        )
        record_audit_event(
            action="COOPERATION_SETTLEMENT_CREATED", resource_type="CooperationSettlement",
            resource_id=str(settlement.id), actor=ctx.user, agency_id=ctx.agency_id,
            after_state={"amount": str(settlement.amount), "currency": settlement.currency_code,
                         "split_percent": str(settlement.split_percent)}
        )
        return {"id": str(settlement.id), "status": settlement.status,
                "amount": str(settlement.amount), "currency_code": settlement.currency_code,
                "split_percent": str(settlement.split_percent),
                "note": "این رکورد، گردش تأیید تسویه است و وجهی جابه‌جا نمی‌کند."}
    return ok(await run_django(op, agency_id=ctx.agency_id, user_id=ctx.user.id))


@router.patch("/cooperations/{cooperation_id}/settlements/{settlement_id}")
async def transition_cooperation_settlement(
    cooperation_id: UUID, settlement_id: UUID, body: SettlementTransition,
    ctx: RequestContext = Depends(require_agency_context)
):
    def op():
        from apps.ecosystem.models import CooperationSettlement
        from apps.audit.services import record_audit_event
        from common.permissions import is_super_admin
        settlement = CooperationSettlement.objects.select_for_update().filter(
            id=settlement_id, cooperation_id=cooperation_id
        ).select_related("cooperation").first()
        if not settlement:
            raise HTTPException(404, "تسویه همکاری یافت نشد.")
        if body.status not in CooperationSettlement.Status.values:
            raise HTTPException(400, "وضعیت تسویه نامعتبر است.")
        old = settlement.status
        actor_agency = ctx.agency_id
        _require_member(ctx.user, actor_agency, "agency.manage_policy")
        if body.status == "PENDING_APPROVAL":
            if actor_agency != settlement.payer_agency_id or old != "DRAFT":
                raise HTTPException(409, "فقط پرداخت‌کننده می‌تواند پیش‌نویس را برای تأیید ارسال کند.")
        elif body.status == "APPROVED":
            if actor_agency != settlement.payee_agency_id or old != "PENDING_APPROVAL":
                raise HTTPException(409, "فقط دریافت‌کننده می‌تواند تسویه را تأیید کند.")
            settlement.approved_by = ctx.user
            settlement.approved_at = timezone.now()
        elif body.status == "PAID":
            if actor_agency != settlement.payee_agency_id or old != "APPROVED":
                raise HTTPException(409, "ثبت دریافت وجه فقط پس از تأیید و توسط دریافت‌کننده مجاز است.")
            if not body.external_reference.strip():
                raise HTTPException(422, "شناسه پیگیری پرداخت الزامی است.")
            settlement.paid_at = timezone.now()
            settlement.external_reference = body.external_reference.strip()
        elif body.status == "CANCELLED":
            if old in ["PAID", "CANCELLED"] or actor_agency not in [settlement.payer_agency_id, settlement.payee_agency_id]:
                raise HTTPException(409, "لغو این تسویه مجاز نیست.")
        else:
            raise HTTPException(409, "انتقال وضعیت درخواست‌شده مجاز نیست.")
        settlement.status = body.status
        settlement.updated_by = ctx.user
        settlement.save()
        record_audit_event(
            action="COOPERATION_SETTLEMENT_STATUS_CHANGED", resource_type="CooperationSettlement",
            resource_id=str(settlement.id), actor=ctx.user, agency_id=ctx.agency_id,
            before_state={"status": old}, after_state={"status": settlement.status,
                "external_reference": settlement.external_reference}
        )
        return {"id": str(settlement.id), "status": settlement.status,
                "approved_at": settlement.approved_at.isoformat() if settlement.approved_at else None,
                "paid_at": settlement.paid_at.isoformat() if settlement.paid_at else None,
                "external_reference": settlement.external_reference}
    return ok(await run_django(op, agency_id=ctx.agency_id, user_id=ctx.user.id))
