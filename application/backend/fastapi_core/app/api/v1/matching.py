from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_optional_context
from app.schemas.common import ok

router = APIRouter(prefix="/matching", tags=["Smart Matching & Market Analytics"])


@router.get("/customer-to-properties")
async def match_properties_for_customer(
    customer_id: Optional[UUID] = None,
    deal_type_id: str = "SALE",
    property_type_id: str = "APARTMENT",
    target_city: str = "تهران",
    districts: str = "زعفرانیه,فرشته",
    min_area_sqm: float = 120,
    max_area_sqm: float = 250,
    min_budget: float = 15000000000,
    max_budget: float = 45000000000,
    min_bedrooms: int = 2,
    amenities: str = "",
    ctx: RequestContext = Depends(get_optional_context),
):
    def _op():
        from apps.properties.models import DealType, Property, PropertyType
        from apps.search.services import score_property_for_requirement

        req = {
            "deal_type_id": None,
            "property_type_id": None,
            "target_city": target_city,
            "target_districts": [d.strip() for d in districts.split(",") if d.strip()],
            "min_area_sqm": Decimal(str(min_area_sqm)),
            "max_area_sqm": Decimal(str(max_area_sqm)),
            "min_budget": Decimal(str(min_budget)),
            "max_budget": Decimal(str(max_budget)),
            "min_bedrooms": min_bedrooms,
            "preferred_amenities": [a.strip().upper() for a in amenities.split(",") if a.strip()],
            "currency_id": "IRT",
        }

        if customer_id:
            if not ctx.user or not ctx.agency_id:
                from common.exceptions import PermissionDeniedDomainError
                raise PermissionDeniedDomainError("برای تطبیق بر اساس پرونده مشتری باید وارد آژانس شوید.")
            from apps.customers.models import CustomerRequirement
            from apps.customers.services import list_customers
            customer = list_customers(user=ctx.user, agency_id=ctx.agency_id).filter(
                id=customer_id, is_deleted=False
            ).first()
            if not customer:
                from common.exceptions import NotFoundDomainError
                raise NotFoundDomainError("مشتری یافت نشد یا در محدوده دسترسی شما نیست.")
            requirement = CustomerRequirement.objects.all_tenants().filter(
                customer=customer, agency_id=ctx.agency_id, is_active=True
            ).order_by("-created_at").first()
            if not requirement:
                from common.exceptions import NotFoundDomainError
                raise NotFoundDomainError("برای این مشتری نیاز فعال جستجوی ملک ثبت نشده است.")
            req = {
                "deal_type_id": requirement.deal_type_id,
                "property_type_id": requirement.property_type_id,
                "target_city": requirement.target_city,
                "target_districts": requirement.target_districts or [],
                "min_area_sqm": requirement.min_area_sqm,
                "max_area_sqm": requirement.max_area_sqm,
                "min_budget": requirement.min_budget,
                "max_budget": requirement.max_budget,
                "min_bedrooms": requirement.min_bedrooms,
                "preferred_amenities": requirement.required_amenities or [],
                "currency_id": requirement.currency_id,
            }
        else:
            deal_type = DealType.objects.filter(code=deal_type_id, is_active=True).first()
            property_type = PropertyType.objects.filter(code=property_type_id, is_active=True).first()
            req["deal_type_id"] = deal_type.id if deal_type else None
            req["property_type_id"] = property_type.id if property_type else None

        def _score_queryset(qs):
            if req["deal_type_id"]:
                qs = qs.filter(deal_type_id=req["deal_type_id"])
            if req["property_type_id"]:
                qs = qs.filter(property_type_id=req["property_type_id"])
            if req["target_city"]:
                qs = qs.filter(location__city=req["target_city"])
            if req["target_districts"]:
                qs = qs.filter(location__district__in=req["target_districts"])
            if req["min_area_sqm"] is not None:
                qs = qs.filter(built_area_sqm__gte=req["min_area_sqm"])
            if req["max_area_sqm"] is not None:
                qs = qs.filter(built_area_sqm__lte=req["max_area_sqm"])
            if req["min_bedrooms"]:
                qs = qs.filter(bedrooms__gte=req["min_bedrooms"])
            if req["currency_id"]:
                qs = qs.filter(currency_id=req["currency_id"])
            if req["max_budget"] and Decimal(str(req["max_budget"])) > 0:
                qs = qs.filter(total_price__gte=req["min_budget"], total_price__lte=req["max_budget"])
            qs = qs.select_related("location", "property_type", "deal_type").prefetch_related("amenities")[:500]
            props = []
            for prop in qs:
                loc = getattr(prop, "location", None)
                props.append({
                    "id": str(prop.id),
                    "property_code": prop.property_code,
                    "title": prop.title,
                    "property_type_id": prop.property_type_id,
                    "deal_type_id": prop.deal_type_id,
                    "built_area_sqm": prop.built_area_sqm,
                    "bedrooms": prop.bedrooms,
                    "total_price": prop.total_price,
                    "currency_id": prop.currency_id,
                    "city": loc.city if loc else "",
                    "district": loc.district if loc else "",
                    "amenity_codes": [a.code for a in prop.amenities.all()],
                })
            return props

        if ctx.user and ctx.agency_id:
            from apps.properties.services import list_agency_properties
            qs = list_agency_properties(user=ctx.user, agency_id=ctx.agency_id).filter(
                status=Property.Status.PUBLISHED
            )
            props = _score_queryset(qs)
        else:
            from common.tenant.context import tenant_bypass
            with tenant_bypass(reason="public_catalog"):
                qs = Property.objects.all_tenants().filter(
                    is_deleted=False,
                    status=Property.Status.PUBLISHED,
                    visibility=Property.Visibility.PUBLIC_PORTAL,
                )
                props = _score_queryset(qs)
        scored = [score_property_for_requirement(prop, req) for prop in props]
        scored.sort(key=lambda item: item["match_score"], reverse=True)
        return scored[:10]

    return ok(await run_django(
        _op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None
    ))


@router.get("/analytics/price-trends")
async def district_price_trends(
    city: str = Query(default="تهران"),
    currency_code: str = Query(default="IRT", min_length=3, max_length=10),
):
    def _op():
        from django.db.models import Avg, Count
        from apps.properties.models import Property

        from common.tenant.context import tenant_bypass
        with tenant_bypass(reason="public_catalog"):
            rows = list(
                Property.objects.all_tenants()
            .filter(
                is_deleted=False,
                status=Property.Status.PUBLISHED,
                visibility=Property.Visibility.PUBLIC_PORTAL,
                currency_id=currency_code,
                price_per_sqm__gt=Decimal("0"),
                location__city=city,
            )
            .values("location__district", "currency_id")
            .annotate(
                listing_count=Count("id"),
                avg_price_per_sqm=Avg("price_per_sqm"),
            )
                .filter(listing_count__gte=5)
                .order_by("-avg_price_per_sqm")
            )
        return [
            {
                "district": row["location__district"] or "سایر",
                "listing_count": row["listing_count"],
                "currency": row["currency_id"],
                "avg_price_per_sqm": str(int(row["avg_price_per_sqm"] or 0)),
            }
            for row in rows
        ]

    return ok(await run_django(_op))
