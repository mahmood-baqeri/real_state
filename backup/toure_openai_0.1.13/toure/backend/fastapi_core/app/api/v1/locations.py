from decimal import Decimal
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context
from app.schemas.common import ok

router = APIRouter(prefix="/locations", tags=["Hierarchical Geography"])


class ProvinceCreateBody(BaseModel):
    country_id: str = "IR"
    code: str = ""
    name_fa: str = Field(min_length=2, max_length=100)
    name_en: str = ""
    center_lat: Optional[Decimal] = None
    center_lng: Optional[Decimal] = None
    sort_order: int = 100
    is_active: bool = True


class CityCreateBody(BaseModel):
    province_id: UUID
    name_fa: str = Field(min_length=2, max_length=100)
    name_en: str = ""
    center_lat: Optional[Decimal] = None
    center_lng: Optional[Decimal] = None
    sort_order: int = 100
    is_active: bool = True


class DistrictCreateBody(BaseModel):
    city_id: UUID
    name_fa: str = Field(min_length=2, max_length=100)
    name_en: str = ""
    center_lat: Optional[Decimal] = None
    center_lng: Optional[Decimal] = None
    sort_order: int = 100
    is_active: bool = True


class NeighborhoodCreateBody(BaseModel):
    district_id: UUID
    name_fa: str = Field(min_length=2, max_length=100)
    name_en: str = ""
    center_lat: Optional[Decimal] = None
    center_lng: Optional[Decimal] = None
    sort_order: int = 100
    is_active: bool = True


class GeoNodePatchBody(BaseModel):
    is_active: Optional[bool] = None
    name_fa: Optional[str] = None


def _ser_node(n, extra: Optional[dict] = None) -> dict:
    payload = {
        "id": str(n.id),
        "name_fa": n.name_fa,
        "name_en": n.name_en,
        "slug": n.slug,
        "center_lat": str(n.center_lat) if n.center_lat is not None else None,
        "center_lng": str(n.center_lng) if n.center_lng is not None else None,
        "sort_order": n.sort_order,
        "is_active": n.is_active,
    }
    if extra:
        payload.update(extra)
    return payload


@router.get("/provinces")
async def list_provinces_endpoint(
    country_id: str = "IR",
    q: Optional[str] = None,
    active_only: bool = True,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
):
    def _op():
        from apps.settings.services import list_provinces
        from common.pagination import paginate_queryset

        qs = list_provinces(country_id=country_id, q=q, active_only=active_only)
        return paginate_queryset(
            qs,
            page=page,
            page_size=page_size,
            serializer_fn=lambda p: _ser_node(p, {"country_id": p.country_id, "code": p.code}),
        )

    items, meta = await run_django(_op)
    return ok(items, meta=meta)


@router.get("/cities")
async def list_cities_endpoint(
    province_id: Optional[UUID] = None,
    q: Optional[str] = None,
    active_only: bool = True,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
):
    def _op():
        from apps.settings.services import list_cities
        from common.pagination import paginate_queryset

        qs = list_cities(province_id=province_id, q=q, active_only=active_only)
        return paginate_queryset(
            qs,
            page=page,
            page_size=page_size,
            serializer_fn=lambda c: _ser_node(
                c,
                {"province_id": str(c.province_id), "province_name": c.province.name_fa},
            ),
        )

    items, meta = await run_django(_op)
    return ok(items, meta=meta)


@router.get("/districts")
async def list_districts_endpoint(
    city_id: Optional[UUID] = None,
    q: Optional[str] = None,
    active_only: bool = True,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
):
    def _op():
        from apps.settings.services import list_districts
        from common.pagination import paginate_queryset

        qs = list_districts(city_id=city_id, q=q, active_only=active_only)
        return paginate_queryset(
            qs,
            page=page,
            page_size=page_size,
            serializer_fn=lambda d: _ser_node(
                d,
                {"city_id": str(d.city_id), "city_name": d.city.name_fa},
            ),
        )

    items, meta = await run_django(_op)
    return ok(items, meta=meta)


@router.get("/neighborhoods")
async def list_neighborhoods_endpoint(
    district_id: Optional[UUID] = None,
    city_id: Optional[UUID] = None,
    q: Optional[str] = None,
    active_only: bool = True,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
):
    def _op():
        from apps.settings.services import list_neighborhoods
        from common.pagination import paginate_queryset

        qs = list_neighborhoods(district_id=district_id, city_id=city_id, q=q, active_only=active_only)
        return paginate_queryset(
            qs,
            page=page,
            page_size=page_size,
            serializer_fn=lambda n: _ser_node(
                n,
                {
                    "district_id": str(n.district_id),
                    "district_name": n.district.name_fa,
                    "city_id": str(n.district.city_id),
                    "city_name": n.district.city.name_fa,
                },
            ),
        )

    items, meta = await run_django(_op)
    return ok(items, meta=meta)


@router.post("/provinces", status_code=201)
async def create_province_endpoint(
    body: ProvinceCreateBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.settings.services import create_province

        p = create_province(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return _ser_node(p, {"country_id": p.country_id, "code": p.code})

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/cities", status_code=201)
async def create_city_endpoint(
    body: CityCreateBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.settings.services import create_city

        c = create_city(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return _ser_node(c, {"province_id": str(c.province_id), "province_name": c.province.name_fa})

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/districts", status_code=201)
async def create_district_endpoint(
    body: DistrictCreateBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.settings.services import create_district

        d = create_district(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return _ser_node(d, {"city_id": str(d.city_id), "city_name": d.city.name_fa})

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/neighborhoods", status_code=201)
async def create_neighborhood_endpoint(
    body: NeighborhoodCreateBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.settings.services import create_neighborhood

        n = create_neighborhood(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return _ser_node(n, {"district_id": str(n.district_id), "district_name": n.district.name_fa})

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.patch("/{level}/{node_id}")
async def patch_geo_node_endpoint(
    level: str,
    node_id: UUID,
    body: GeoNodePatchBody,
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.settings.services import toggle_geo_node

        node = toggle_geo_node(
            user=ctx.user,
            agency_id=ctx.agency_id,
            level=level,
            node_id=node_id,
            is_active=body.is_active,
            name_fa=body.name_fa,
        )
        return _ser_node(node)

    return ok(await run_django(_op, agency_id=ctx.agency_id))
