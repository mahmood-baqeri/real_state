from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_optional_context
from app.schemas.common import ok

router = APIRouter(prefix="/search", tags=["Search Engine"])


@router.get("/properties")
async def search_properties(
    city: Optional[str] = Query(default=None),
    district: Optional[str] = Query(default=None),
    deal_type: Optional[str] = Query(default=None),
    property_type: Optional[str] = Query(default=None),
    min_price: Optional[Decimal] = Query(default=None),
    max_price: Optional[Decimal] = Query(default=None),
    min_area: Optional[Decimal] = Query(default=None),
    min_bedrooms: Optional[int] = Query(default=None),
    q: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    ctx: RequestContext = Depends(get_optional_context),
):
    def _op():
        from apps.properties.services import list_public_properties
        from common.pagination import paginate_queryset

        qs = list_public_properties(
            city=city,
            district=district,
            deal_type=deal_type,
            property_type=property_type,
            min_price=min_price,
            max_price=max_price,
            min_area=min_area,
            min_bedrooms=min_bedrooms,
            q=q,
        )

        def _ser(p):
            loc = getattr(p, "location", None)
            cover = next((m.url for m in p.media_items.all() if m.is_public and m.is_cover), None)
            if not cover:
                cover = next((m.url for m in p.media_items.all() if m.is_public), None)
            return {
                "id": str(p.id),
                "property_code": p.property_code,
                "title": p.title,
                "property_type_id": p.property_type_id,
                "property_type_name": p.property_type.name_fa,
                "deal_type_id": p.deal_type_id,
                "deal_type_name": p.deal_type.name_fa,
                "built_area_sqm": str(p.built_area_sqm),
                "bedrooms": p.bedrooms,
                "total_price": str(p.total_price),
                "price_per_sqm": str(p.price_per_sqm),
                "deposit_amount": str(p.deposit_amount),
                "rent_amount": str(p.rent_amount),
                "currency_id": p.currency_id,
                "is_featured": p.is_featured,
                "city": loc.city if loc else "",
                "district": loc.district if loc else "",
                "neighborhood": loc.neighborhood if loc else "",
                "agency_name": p.agency.name,
                "cover_url": cover,
            }

        return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser)

    items, meta = await run_django(_op)
    meta["engine"] = "fastapi-django-orm"
    return ok(items, meta=meta)
