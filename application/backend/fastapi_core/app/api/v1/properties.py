from decimal import Decimal
from typing import Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_current_context, get_optional_context, require_agency_context
from app.schemas.common import ok

router = APIRouter(prefix="/properties", tags=["Properties & Media"])


class PropertyLocationBody(BaseModel):
    country_id: str = "IR"
    province_id: Optional[UUID] = None
    city_id: Optional[UUID] = None
    district_id: Optional[UUID] = None
    neighborhood_id: Optional[UUID] = None
    province: str = "تهران"
    city: str = ""
    district: str = ""
    neighborhood: str = ""
    street: str = ""
    full_address: str = ""
    postal_code: str = ""
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    hide_exact_address: bool = True


class AmenityValueInput(BaseModel):
    code: str
    value_text: str = ""
    value_number: Optional[Decimal] = None


class AmenityCategoryCreateBody(BaseModel):
    code: str
    name_fa: str
    name_en: str = ""
    icon_name: str = ""
    description: str = ""
    sort_order: int = 100
    is_active: bool = True


class AmenityUpsertBody(BaseModel):
    code: str
    category_code: Optional[str] = None
    name_fa: str
    name_en: str = ""
    icon_name: str = ""
    description: str = ""
    value_type: str = "BOOLEAN"
    unit_label: str = ""
    options_json: list[str] = []
    sort_order: int = 100
    is_active: bool = True


class AmenityToggleBody(BaseModel):
    is_active: bool


class PropertyCreateBody(BaseModel):
    property_code: str
    title: str
    description: str = ""
    property_type_id: str
    deal_type_id: str
    usage_type: str = "مسکونی"
    visibility: str = "PRIVATE_AGENCY"
    is_featured: bool = False
    branch_id: Optional[UUID] = None
    land_area_sqm: Decimal = Decimal("0")
    built_area_sqm: Decimal = Decimal("0")
    bedrooms: int = 0
    bathrooms: int = 0
    floor_number: Optional[int] = None
    total_floors: Optional[int] = None
    units_per_floor: Optional[int] = None
    building_age: Optional[int] = None
    construction_year: Optional[int] = None
    deed_type: str = "تک‌برگ"
    deed_status: str = "آزاد"
    orientation: str = ""
    facade_type: str = ""
    currency_id: str = "IRT"
    total_price: Decimal = Decimal("0")
    deposit_amount: Decimal = Decimal("0")
    rent_amount: Decimal = Decimal("0")
    min_acceptable_price: Optional[Decimal] = None
    is_negotiable: bool = True
    is_exclusive: bool = False
    amenity_codes: list[str] = []
    amenity_values: list[AmenityValueInput] = []
    owner_customer_id: Optional[UUID] = None
    initial_media_url: Optional[str] = None
    location: Optional[PropertyLocationBody] = None


class PropertyPatchBody(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    property_type_id: Optional[str] = None
    deal_type_id: Optional[str] = None
    usage_type: Optional[str] = None
    visibility: Optional[str] = None
    is_featured: Optional[bool] = None
    land_area_sqm: Optional[Decimal] = None
    built_area_sqm: Optional[Decimal] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    floor_number: Optional[int] = None
    total_floors: Optional[int] = None
    building_age: Optional[int] = None
    deed_type: Optional[str] = None
    deed_status: Optional[str] = None
    total_price: Optional[Decimal] = None
    deposit_amount: Optional[Decimal] = None
    rent_amount: Optional[Decimal] = None
    min_acceptable_price: Optional[Decimal] = None
    is_negotiable: Optional[bool] = None
    is_exclusive: Optional[bool] = None
    amenity_codes: Optional[list[str]] = None
    amenity_values: Optional[list[AmenityValueInput]] = None
    location: Optional[PropertyLocationBody] = None


class PropertyStatusBody(BaseModel):
    status: str
    reason: str = ""


class PropertyMediaBody(BaseModel):
    media_type: str = "IMAGE"
    url: str
    title: str = ""
    is_cover: bool = False
    is_public: bool = True


class MediaReorderBody(BaseModel):
    ordered_media_ids: list[UUID]
    cover_media_id: Optional[UUID] = None


def _ser_amenity_item(a, value_map: Optional[dict] = None) -> dict:
    val_obj = (value_map or {}).get(a.code)
    return {
        "code": a.code,
        "name_fa": a.name_fa,
        "name_en": a.name_en,
        "category_code": a.category_id,
        "category_name_fa": a.category.name_fa if a.category else "سایر امکانات",
        "value_type": a.value_type,
        "unit_label": a.unit_label,
        "value_text": val_obj.value_text if val_obj else "",
        "value_number": str(val_obj.value_number) if (val_obj and val_obj.value_number is not None) else None,
    }


def _ser_public_property(p, include_history: bool = False) -> dict:
    loc = getattr(p, "location", None)
    loc_dict = None
    if loc:
        lat = str(loc.latitude) if (loc.latitude and not loc.hide_exact_address) else (
            str(loc.latitude.quantize(Decimal("0.01"))) if loc.latitude else None
        )
        lng = str(loc.longitude) if (loc.longitude and not loc.hide_exact_address) else (
            str(loc.longitude.quantize(Decimal("0.01"))) if loc.longitude else None
        )
        loc_dict = {
            "country": loc.country_id,
            "province_id": str(loc.province_ref_id) if loc.province_ref_id else None,
            "city_id": str(loc.city_ref_id) if loc.city_ref_id else None,
            "district_id": str(loc.district_ref_id) if loc.district_ref_id else None,
            "neighborhood_id": str(loc.neighborhood_ref_id) if loc.neighborhood_ref_id else None,
            "province": loc.province,
            "city": loc.city,
            "district": loc.district,
            "neighborhood": loc.neighborhood,
            "hide_exact_address": loc.hide_exact_address,
            "latitude": lat,
            "longitude": lng,
        }
    value_map = {av.amenity_id: av for av in p.amenity_values.all()}
    media_sorted = sorted(
        [m for m in p.media_items.all() if m.is_public],
        key=lambda m: (0 if m.is_cover else 1, m.sort_order, m.created_at),
    )
    data = {
        "id": str(p.id),
        "property_code": p.property_code,
        "title": p.title,
        "description": p.description,
        "property_type": {
            "code": p.property_type.code,
            "name_fa": p.property_type.name_fa,
            "name_en": p.property_type.name_en,
            "category": p.property_type.category,
        },
        "deal_type": {
            "code": p.deal_type.code,
            "name_fa": p.deal_type.name_fa,
            "name_en": p.deal_type.name_en,
            "is_rental": p.deal_type.is_rental,
        },
        "usage_type": p.usage_type,
        "status": p.status,
        "is_featured": p.is_featured,
        "land_area_sqm": str(p.land_area_sqm),
        "built_area_sqm": str(p.built_area_sqm),
        "bedrooms": p.bedrooms,
        "bathrooms": p.bathrooms,
        "floor_number": p.floor_number,
        "total_floors": p.total_floors,
        "building_age": p.building_age,
        "deed_type": p.deed_type,
        "currency": p.currency_id,
        "total_price": str(p.total_price),
        "price_per_sqm": str(p.price_per_sqm),
        "deposit_amount": str(p.deposit_amount),
        "rent_amount": str(p.rent_amount),
        "is_negotiable": p.is_negotiable,
        "amenities": [_ser_amenity_item(a, value_map) for a in p.amenities.all()],
        "location": loc_dict,
        "media_items": [
            {
                "id": str(m.id),
                "media_type": m.media_type,
                "url": m.url,
                "title": m.title,
                "is_cover": m.is_cover,
                "is_public": m.is_public,
                "sort_order": m.sort_order,
            }
            for m in media_sorted
        ],
        "agency_id": str(p.agency_id),
        "agency_name": p.agency.name,
        "view_count": p.view_count,
        "created_at": p.created_at.isoformat(),
    }
    if include_history:
        data["price_history"] = [
            {
                "id": str(ph.id),
                "previous_price": str(ph.previous_price),
                "new_price": str(ph.new_price),
                "currency_code": ph.currency_code,
                "changed_at": ph.changed_at.isoformat(),
            }
            for ph in p.price_history.all().order_by("changed_at")
        ]
        data["status_history"] = [
            {
                "id": str(sh.id),
                "from_status": sh.from_status,
                "to_status": sh.to_status,
                "reason": sh.reason,
                "changed_at": sh.changed_at.isoformat(),
            }
            for sh in p.status_history.all().order_by("-changed_at")
        ]
    return data


def _ser_agency_property(p, user, include_history: bool = False) -> dict:
    from apps.properties.services import serialize_property_owners

    loc = getattr(p, "location", None)
    loc_dict = None
    if loc:
        loc_dict = {
            "country_id": loc.country_id,
            "province_id": str(loc.province_ref_id) if loc.province_ref_id else None,
            "city_id": str(loc.city_ref_id) if loc.city_ref_id else None,
            "district_id": str(loc.district_ref_id) if loc.district_ref_id else None,
            "neighborhood_id": str(loc.neighborhood_ref_id) if loc.neighborhood_ref_id else None,
            "province": loc.province,
            "city": loc.city,
            "district": loc.district,
            "neighborhood": loc.neighborhood,
            "street": loc.street,
            "full_address": loc.full_address,
            "postal_code": loc.postal_code,
            "latitude": str(loc.latitude) if loc.latitude else None,
            "longitude": str(loc.longitude) if loc.longitude else None,
            "hide_exact_address": loc.hide_exact_address,
        }
    return {
        **_ser_public_property(p, include_history=include_history),
        "branch_id": str(p.branch_id) if p.branch_id else None,
        "property_type_id": p.property_type_id,
        "deal_type_id": p.deal_type_id,
        "visibility": p.visibility,
        "deed_status": p.deed_status,
        "min_acceptable_price": str(p.min_acceptable_price) if p.min_acceptable_price is not None else None,
        "is_exclusive": p.is_exclusive,
        "inquiry_count": p.inquiry_count,
        "location": loc_dict,
        "owners": serialize_property_owners(user, p),
        "assigned_agents": [
            {
                "membership_id": str(a.membership_id),
                "full_name": a.membership.user.full_name,
                "role": a.role,
            }
            for a in p.agent_assignments.all()
        ],
    }


@router.get("/catalog")
async def catalog(include_inactive: bool = False):
    def _op():
        from apps.properties.services import get_property_catalog

        cat = get_property_catalog(include_inactive=include_inactive)
        return {
            "property_types": [
                {"code": pt.code, "name_fa": pt.name_fa, "name_en": pt.name_en, "category": pt.category}
                for pt in cat["property_types"]
            ],
            "deal_types": [
                {"code": dt.code, "name_fa": dt.name_fa, "name_en": dt.name_en, "is_rental": dt.is_rental}
                for dt in cat["deal_types"]
            ],
            "amenity_categories": [
                {
                    "code": c.code,
                    "name_fa": c.name_fa,
                    "name_en": c.name_en,
                    "icon_name": c.icon_name,
                    "sort_order": c.sort_order,
                    "is_active": c.is_active,
                }
                for c in cat["amenity_categories"]
            ],
            "amenities": [
                {
                    "code": am.code,
                    "category_code": am.category_id,
                    "category_name_fa": am.category.name_fa if am.category else "سایر امکانات",
                    "name_fa": am.name_fa,
                    "name_en": am.name_en,
                    "icon_name": am.icon_name,
                    "value_type": am.value_type,
                    "unit_label": am.unit_label,
                    "options_json": am.options_json,
                    "sort_order": am.sort_order,
                    "is_active": am.is_active,
                }
                for am in cat["amenities"]
            ],
        }

    return ok(await run_django(_op))


@router.post("/amenity-categories", status_code=201)
async def create_amenity_category_endpoint(
    body: AmenityCategoryCreateBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.properties.services import create_amenity_category

        c = create_amenity_category(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return {"code": c.code, "name_fa": c.name_fa, "is_active": c.is_active}

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/amenities", status_code=201)
async def upsert_amenity_endpoint(
    body: AmenityUpsertBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.properties.services import upsert_amenity

        am = upsert_amenity(user=ctx.user, agency_id=ctx.agency_id, data=body.model_dump())
        return {
            "code": am.code,
            "category_code": am.category_id,
            "name_fa": am.name_fa,
            "value_type": am.value_type,
            "unit_label": am.unit_label,
            "is_active": am.is_active,
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.patch("/amenities/{code}")
async def toggle_amenity_endpoint(
    code: str, body: AmenityToggleBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.properties.services import toggle_amenity_status

        am = toggle_amenity_status(
            user=ctx.user, agency_id=ctx.agency_id, code=code, is_active=body.is_active
        )
        return {"code": am.code, "is_active": am.is_active}

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/compare")
async def compare_properties(
    ids: str = Query(..., description="Comma-separated property UUIDs (2 to 4)"),
    ctx: RequestContext = Depends(get_optional_context),
):
    raw_ids = [s.strip() for s in ids.split(",") if s.strip()][:4]

    def _op():
        from apps.properties.services import get_property_for_context

        items = []
        for raw_id in raw_ids:
            try:
                pid = UUID(raw_id)
                prop, is_internal = get_property_for_context(
                    user=ctx.user, agency_id=ctx.agency_id, property_id=pid
                )
                items.append(
                    _ser_agency_property(prop, ctx.user, include_history=True)
                    if is_internal
                    else _ser_public_property(prop, include_history=True)
                )
            except Exception:
                continue
        return items

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/public")
async def list_public(
    province_id: Optional[UUID] = None,
    city_id: Optional[UUID] = None,
    district_id: Optional[UUID] = None,
    neighborhood_id: Optional[UUID] = None,
    city: Optional[str] = None,
    district: Optional[str] = None,
    deal_type: Optional[str] = None,
    property_type: Optional[str] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    min_area: Optional[Decimal] = None,
    max_area: Optional[Decimal] = None,
    min_bedrooms: Optional[int] = None,
    amenities: Optional[str] = None,
    min_lat: Optional[Decimal] = None,
    max_lat: Optional[Decimal] = None,
    min_lng: Optional[Decimal] = None,
    max_lng: Optional[Decimal] = None,
    polygon: Optional[str] = None,
    q: Optional[str] = None,
    featured: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
            featured_only=featured,
        )
        return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser_public_property)

    items, meta = await run_django(_op)
    return ok(items, meta=meta)


@router.get("")
async def list_properties(
    status: Optional[str] = None,
    deal_type: Optional[str] = None,
    property_type: Optional[str] = None,
    province_id: Optional[UUID] = None,
    city_id: Optional[UUID] = None,
    district_id: Optional[UUID] = None,
    neighborhood_id: Optional[UUID] = None,
    q: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(get_optional_context),
):
    def _op():
        from apps.properties.services import list_agency_properties, list_public_properties
        from common.pagination import paginate_queryset

        if not ctx.is_authenticated or (not ctx.agency_id and ctx.user.platform_role == "CUSTOMER"):
            qs = list_public_properties(
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                neighborhood_id=neighborhood_id,
                deal_type=deal_type,
                property_type=property_type,
                q=q,
            )
            return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser_public_property)

        qs = list_agency_properties(
            user=ctx.user,
            agency_id=ctx.agency_id,
            status_filter=status,
            deal_type=deal_type,
            property_type=property_type,
            province_id=province_id,
            city_id=city_id,
            district_id=district_id,
            neighborhood_id=neighborhood_id,
            q=q,
        )
        return paginate_queryset(
            qs, page=page, page_size=page_size, serializer_fn=lambda p: _ser_agency_property(p, ctx.user)
        )

    items, meta = await run_django(_op, agency_id=ctx.agency_id)
    return ok(items, meta=meta)


@router.post("", status_code=201)
async def create_property_endpoint(
    body: PropertyCreateBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.properties.services import create_property

        data = body.model_dump()
        prop = create_property(user=ctx.user, agency_id=ctx.agency_id, data=data)
        return _ser_agency_property(prop, ctx.user, include_history=True)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/{property_id}")
async def get_property(property_id: UUID, ctx: RequestContext = Depends(get_optional_context)):
    def _op():
        from apps.properties.services import get_property_for_context, get_related_properties

        prop, is_internal = get_property_for_context(
            user=ctx.user, agency_id=ctx.agency_id, property_id=property_id
        )
        payload = (
            _ser_agency_property(prop, ctx.user, include_history=True)
            if is_internal
            else _ser_public_property(prop, include_history=True)
        )
        payload["related_properties"] = [_ser_public_property(rp) for rp in get_related_properties(prop=prop, limit=3)]
        return payload

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/{property_id}/timeline")
async def get_property_timeline_endpoint(property_id: UUID, ctx: RequestContext = Depends(get_optional_context)):
    def _op():
        from apps.properties.services import get_property_timeline

        return get_property_timeline(user=ctx.user, agency_id=ctx.agency_id, property_id=property_id)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.get("/{property_id}/related")
async def get_related_properties_endpoint(property_id: UUID, ctx: RequestContext = Depends(get_optional_context)):
    def _op():
        from apps.properties.services import get_property_for_context, get_related_properties

        prop, _ = get_property_for_context(user=ctx.user, agency_id=ctx.agency_id, property_id=property_id)
        return [_ser_public_property(rp) for rp in get_related_properties(prop=prop, limit=4)]

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.patch("/{property_id}")
async def patch_property(
    property_id: UUID, body: PropertyPatchBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.properties.services import update_property

        prop = update_property(
            user=ctx.user,
            agency_id=ctx.agency_id,
            property_id=property_id,
            data=body.model_dump(exclude_none=True),
        )
        return _ser_agency_property(prop, ctx.user, include_history=True)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.delete("/{property_id}")
async def delete_property(property_id: UUID, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.properties.services import soft_delete_property

        soft_delete_property(user=ctx.user, agency_id=ctx.agency_id, property_id=property_id)
        return {"deleted": True}

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/{property_id}/submit")
async def submit_property(property_id: UUID, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.properties.models import Property
        from apps.properties.services import transition_property_status

        prop = transition_property_status(
            user=ctx.user,
            agency_id=ctx.agency_id,
            property_id=property_id,
            to_status=Property.Status.PENDING_APPROVAL,
        )
        return _ser_agency_property(prop, ctx.user, include_history=True)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/{property_id}/publish")
async def publish_property(property_id: UUID, ctx: RequestContext = Depends(require_agency_context)):
    def _op():
        from apps.properties.models import Property
        from apps.properties.services import transition_property_status

        prop = transition_property_status(
            user=ctx.user,
            agency_id=ctx.agency_id,
            property_id=property_id,
            to_status=Property.Status.PUBLISHED,
        )
        return _ser_agency_property(prop, ctx.user, include_history=True)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/{property_id}/status")
async def set_property_status(
    property_id: UUID, body: PropertyStatusBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.properties.services import transition_property_status

        prop = transition_property_status(
            user=ctx.user,
            agency_id=ctx.agency_id,
            property_id=property_id,
            to_status=body.status,
            reason=body.reason,
        )
        return _ser_agency_property(prop, ctx.user, include_history=True)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/{property_id}/media", status_code=201)
async def add_media(
    property_id: UUID, body: PropertyMediaBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.properties.services import add_property_media

        m = add_property_media(
            user=ctx.user,
            agency_id=ctx.agency_id,
            property_id=property_id,
            **body.model_dump(),
        )
        return {"id": str(m.id), "url": m.url, "is_cover": m.is_cover, "sort_order": m.sort_order}

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/{property_id}/media/upload", status_code=201)
async def upload_media_file(
    property_id: UUID,
    file: UploadFile = File(...),
    title: str = Form(""),
    is_cover: bool = Form(False),
    is_public: bool = Form(True),
    ctx: RequestContext = Depends(require_agency_context),
):
    content = await file.read()

    def _op():
        from apps.properties.services import upload_property_media_file

        m = upload_property_media_file(
            user=ctx.user,
            agency_id=ctx.agency_id,
            property_id=property_id,
            filename=file.filename or "image.png",
            content_type=file.content_type or "",
            content=content,
            title=title,
            is_cover=is_cover,
            is_public=is_public,
        )
        return {
            "id": str(m.id),
            "media_type": m.media_type,
            "url": m.url,
            "title": m.title,
            "is_cover": m.is_cover,
            "is_public": m.is_public,
            "sort_order": m.sort_order,
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/{property_id}/media/reorder")
async def reorder_media_endpoint(
    property_id: UUID, body: MediaReorderBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.properties.services import reorder_property_media

        items = reorder_property_media(
            user=ctx.user,
            agency_id=ctx.agency_id,
            property_id=property_id,
            ordered_media_ids=body.ordered_media_ids,
            cover_media_id=body.cover_media_id,
        )
        return [
            {
                "id": str(m.id),
                "url": m.url,
                "title": m.title,
                "is_cover": m.is_cover,
                "sort_order": m.sort_order,
            }
            for m in items
        ]

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.delete("/{property_id}/media/{media_id}")
async def remove_media(
    property_id: UUID, media_id: UUID, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.properties.services import delete_property_media

        delete_property_media(user=ctx.user, agency_id=ctx.agency_id, property_id=property_id, media_id=media_id)
        return {"deleted": True}

    return ok(await run_django(_op, agency_id=ctx.agency_id))
