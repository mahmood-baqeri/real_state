from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_optional_context
from app.schemas.common import ok
from app.services.matching_service import score_property_for_requirement

router = APIRouter(prefix="/matching", tags=["Smart Matching & Market Analytics"])


@router.get("/customer-to-properties")
async def match_properties_for_customer(
    deal_type_id: str = "SALE",
    property_type_id: str = "APARTMENT",
    target_city: str = "تهران",
    districts: str = "زعفرانیه,فرشته",
    min_area_sqm: float = 120,
    max_area_sqm: float = 250,
    min_budget: float = 15000000000,
    max_budget: float = 45000000000,
    min_bedrooms: int = 2,
    ctx: RequestContext = Depends(get_optional_context),
):
    req = {
        "deal_type_id": deal_type_id,
        "property_type_id": property_type_id,
        "target_city": target_city,
        "target_districts": [d.strip() for d in districts.split(",") if d.strip()],
        "min_area_sqm": min_area_sqm,
        "max_area_sqm": max_area_sqm,
        "min_budget": min_budget,
        "max_budget": max_budget,
        "min_bedrooms": min_bedrooms,
    }

    def _op():
        from apps.properties.models import Property

        qs = (
            Property.objects.all_tenants()
            .filter(is_deleted=False, status=Property.Status.PUBLISHED)
            .select_related("location", "property_type", "deal_type")
        )
        if ctx.agency_id:
            qs = qs.filter(agency_id=ctx.agency_id)
        else:
            qs = qs.filter(visibility=Property.Visibility.PUBLIC_PORTAL)

        props = []
        for p in qs:
            loc = getattr(p, "location", None)
            props.append(
                {
                    "id": str(p.id),
                    "property_code": p.property_code,
                    "title": p.title,
                    "property_type_id": p.property_type_id,
                    "deal_type_id": p.deal_type_id,
                    "built_area_sqm": p.built_area_sqm,
                    "bedrooms": p.bedrooms,
                    "total_price": p.total_price,
                    "city": loc.city if loc else "",
                    "district": loc.district if loc else "",
                }
            )
        scored = [score_property_for_requirement(p, req) for p in props]
        scored.sort(key=lambda item: item["match_score"], reverse=True)
        return scored[:10]

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/analytics/price-trends")
async def district_price_trends(city: str = Query(default="تهران")):
    def _op():
        from django.db.models import Avg, Count
        from apps.properties.models import Property

        rows = (
            Property.objects.all_tenants()
            .filter(
                is_deleted=False,
                price_per_sqm__gt=Decimal("0"),
                location__city=city,
            )
            .values("location__district")
            .annotate(
                listing_count=Count("id"),
                avg_price_per_sqm=Avg("price_per_sqm"),
            )
            .order_by("-avg_price_per_sqm")
        )
        return [
            {
                "district": r["location__district"] or "سایر",
                "listing_count": r["listing_count"],
                "avg_price_per_sqm": str(int(r["avg_price_per_sqm"] or 0)),
            }
            for r in rows
        ]

    return ok(await run_django(_op))
