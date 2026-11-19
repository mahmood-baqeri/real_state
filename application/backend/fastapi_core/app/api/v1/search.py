from decimal import Decimal
from typing import Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context, get_optional_context
from app.schemas.common import ok

router = APIRouter(prefix="/search", tags=["Search Engine & Saved Views"])


class SavedViewCreateBody(BaseModel):
    module: str = Field(min_length=2, max_length=48)
    title: str = Field(min_length=1, max_length=120)
    filters_json: dict[str, Any] = {}
    sort_by: str = ""
    columns_json: list[str] = []
    layout_mode: str = "table"
    is_default: bool = False


@router.get("/properties")
async def search_properties(
    province_id: Optional[UUID] = Query(default=None),
    city_id: Optional[UUID] = Query(default=None),
    district_id: Optional[UUID] = Query(default=None),
    neighborhood_id: Optional[UUID] = Query(default=None),
    city: Optional[str] = Query(default=None),
    district: Optional[str] = Query(default=None),
    deal_type: Optional[str] = Query(default=None),
    property_type: Optional[str] = Query(default=None),
    min_price: Optional[Decimal] = Query(default=None),
    max_price: Optional[Decimal] = Query(default=None),
    min_area: Optional[Decimal] = Query(default=None),
    max_area: Optional[Decimal] = Query(default=None),
    min_bedrooms: Optional[int] = Query(default=None),
    amenities: Optional[str] = Query(default=None, description="Comma-separated amenity codes"),
    min_lat: Optional[Decimal] = Query(default=None),
    max_lat: Optional[Decimal] = Query(default=None),
    min_lng: Optional[Decimal] = Query(default=None),
    max_lng: Optional[Decimal] = Query(default=None),
    polygon: Optional[str] = Query(default=None, description="JSON array of [lat, lng] vertices"),
    q: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    ctx: RequestContext = Depends(get_optional_context),
):
    def _op():
        from apps.properties.services import list_public_properties
        from common.pagination import paginate_queryset

        amenity_codes = [s.strip() for s in amenities.split(",") if s.strip()] if amenities else None
        qs = list_public_properties(
            province_id=province_id,
            city_id=city_id,
            district_id=district_id,
            neighborhood_id=neighborhood_id,
            city=city,
            district=district,
            deal_type=deal_type,
            property_type=property_type,
            min_price=min_price,
            max_price=max_price,
            min_area=min_area,
            max_area=max_area,
            min_bedrooms=min_bedrooms,
            amenity_codes=amenity_codes,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lng=min_lng,
            max_lng=max_lng,
            polygon=polygon,
            q=q,
        )

        def _ser(p):
            loc = getattr(p, "location", None)
            media_sorted = sorted(
                [m for m in p.media_items.all() if m.is_public],
                key=lambda m: (0 if m.is_cover else 1, m.sort_order, m.created_at),
            )
            cover = media_sorted[0].url if media_sorted else None
            lat = None
            lng = None
            if loc and loc.latitude is not None and loc.longitude is not None:
                lat = str(loc.latitude if not loc.hide_exact_address else loc.latitude.quantize(Decimal("0.01")))
                lng = str(loc.longitude if not loc.hide_exact_address else loc.longitude.quantize(Decimal("0.01")))
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
                "province_id": str(loc.province_ref_id) if loc and loc.province_ref_id else None,
                "city_id": str(loc.city_ref_id) if loc and loc.city_ref_id else None,
                "district_id": str(loc.district_ref_id) if loc and loc.district_ref_id else None,
                "neighborhood_id": str(loc.neighborhood_ref_id) if loc and loc.neighborhood_ref_id else None,
                "province": loc.province if loc else "",
                "city": loc.city if loc else "",
                "district": loc.district if loc else "",
                "neighborhood": loc.neighborhood if loc else "",
                "latitude": lat,
                "longitude": lng,
                "amenities": [{"code": a.code, "name_fa": a.name_fa} for a in p.amenities.all()],
                "agency_name": p.agency.name,
                "cover_url": cover,
            }

        return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser)

    items, meta = await run_django(_op)
    meta["engine"] = "fastapi-django-orm"
    meta["spatial_mode"] = "polygon" if polygon else ("bounds" if min_lat is not None else "standard")
    return ok(items, meta=meta)


@router.get("/global")
async def global_search_endpoint(
    q: str = Query(min_length=1, max_length=120),
    limit: int = Query(default=5, ge=1, le=15),
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.search.services import global_search

        return global_search(user=ctx.user, agency_id=ctx.agency_id, query=q, limit=limit)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/views")
async def list_saved_views_endpoint(
    module: Optional[str] = Query(default=None),
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.search.services import list_saved_views

        return [
            {
                "id": str(v.id),
                "module": v.module,
                "title": v.title,
                "filters_json": v.filters_json,
                "sort_by": v.sort_by,
                "columns_json": v.columns_json,
                "layout_mode": v.layout_mode,
                "is_default": v.is_default,
            }
            for v in list_saved_views(user=ctx.user, agency_id=ctx.agency_id, module=module)
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/views", status_code=201)
async def create_saved_view_endpoint(
    body: SavedViewCreateBody,
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.search.services import create_saved_view

        v = create_saved_view(user=ctx.user, agency_id=ctx.agency_id, **body.model_dump())
        return {
            "id": str(v.id),
            "module": v.module,
            "title": v.title,
            "filters_json": v.filters_json,
            "sort_by": v.sort_by,
            "columns_json": v.columns_json,
            "layout_mode": v.layout_mode,
            "is_default": v.is_default,
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.delete("/views/{view_id}")
async def delete_saved_view_endpoint(
    view_id: UUID,
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.search.services import delete_saved_view

        delete_saved_view(user=ctx.user, view_id=view_id)
        return {"deleted": True}

    return ok(await run_django(_op, agency_id=ctx.agency_id))
