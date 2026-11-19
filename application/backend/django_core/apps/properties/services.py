from decimal import Decimal
import json
from typing import Optional
from uuid import UUID
from django.db import models, transaction
from apps.accounts.models import User
from apps.agencies.models import AgencyAccessPolicy
from apps.appointments.models import ViewingAppointment
from apps.audit.services import record_audit_event
from apps.negotiations.models import Negotiation
from apps.property_media.models import PropertyMedia
from apps.settings.services import resolve_location_hierarchy
from common.exceptions import ConflictDomainError, NotFoundDomainError, PermissionDeniedDomainError, ValidationDomainError
from common.permissions import (
    can_edit_property,
    can_view_owner_pii,
    get_active_membership,
    get_agency_policy,
    has_agency_permission,
    is_super_admin,
)
from common.tenant.context import tenant_bypass
from integrations.registry import get_storage_provider
from integrations.storage import validate_uploaded_file
from .models import (
    Amenity,
    AmenityCategory,
    DealType,
    Property,
    PropertyAgentAssignment,
    PropertyAmenityValue,
    PropertyLocation,
    PropertyOwner,
    PropertyPriceHistory,
    PropertyStatusHistory,
    PropertyType,
)


def get_property_catalog(*, include_inactive: bool = False) -> dict:
    cat_qs = AmenityCategory.objects.all() if include_inactive else AmenityCategory.objects.filter(is_active=True)
    am_qs = (
        Amenity.objects.select_related("category").all()
        if include_inactive
        else Amenity.objects.select_related("category").filter(is_active=True)
    )
    return {
        "property_types": list(PropertyType.objects.filter(is_active=True).order_by("name_fa")),
        "deal_types": list(DealType.objects.filter(is_active=True).order_by("name_fa")),
        "amenity_categories": list(cat_qs.order_by("sort_order", "name_fa")),
        "amenities": list(am_qs.order_by("category__sort_order", "sort_order", "name_fa")),
    }


def _assert_catalog_manager(user: User, agency_id: Optional[UUID] = None) -> None:
    if is_super_admin(user):
        return
    if agency_id and has_agency_permission(user, agency_id, "agency.manage_policy"):
        return
    raise PermissionDeniedDomainError("فقط مدیر مجاز می‌تواند دسته‌بندی یا امکانات ملک را مدیریت کند.")


@transaction.atomic
def create_amenity_category(*, user: User, agency_id: Optional[UUID], data: dict) -> AmenityCategory:
    _assert_catalog_manager(user, agency_id)
    code = data["code"].strip().upper()
    if AmenityCategory.objects.filter(code=code).exists():
        raise ConflictDomainError("کد دسته‌بندی امکانات تکراری است.")
    return AmenityCategory.objects.create(
        code=code,
        name_fa=data["name_fa"].strip(),
        name_en=data.get("name_en", "").strip(),
        icon_name=data.get("icon_name", "").strip(),
        description=data.get("description", "").strip(),
        sort_order=int(data.get("sort_order", 100)),
        is_active=bool(data.get("is_active", True)),
    )


@transaction.atomic
def upsert_amenity(*, user: User, agency_id: Optional[UUID], data: dict) -> Amenity:
    _assert_catalog_manager(user, agency_id)
    code = data["code"].strip().upper()
    cat = AmenityCategory.objects.filter(code=data["category_code"]).first() if data.get("category_code") else None
    if data.get("category_code") and not cat:
        raise NotFoundDomainError("دسته‌بندی امکانات یافت نشد.")
    amenity, _ = Amenity.objects.update_or_create(
        code=code,
        defaults={
            "category": cat,
            "name_fa": data["name_fa"].strip(),
            "name_en": data.get("name_en", "").strip(),
            "icon_name": data.get("icon_name", "").strip(),
            "description": data.get("description", "").strip(),
            "value_type": data.get("value_type", Amenity.ValueType.BOOLEAN),
            "unit_label": data.get("unit_label", "").strip(),
            "options_json": data.get("options_json") or [],
            "sort_order": int(data.get("sort_order", 100)),
            "is_active": bool(data.get("is_active", True)),
        },
    )
    return amenity


@transaction.atomic
def toggle_amenity_status(*, user: User, agency_id: Optional[UUID], code: str, is_active: bool) -> Amenity:
    _assert_catalog_manager(user, agency_id)
    am = Amenity.objects.filter(code=code.upper()).first()
    if not am:
        raise NotFoundDomainError("امکانات مورد نظر یافت نشد.")
    am.is_active = bool(is_active)
    am.save(update_fields=["is_active"])
    return am


def parse_polygon_points(raw_polygon: Optional[str]) -> Optional[list[tuple[float, float]]]:
    if not raw_polygon:
        return None
    try:
        parsed = json.loads(raw_polygon)
        if not isinstance(parsed, list) or len(parsed) < 3:
            return None
        pts: list[tuple[float, float]] = []
        for item in parsed:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                pts.append((float(item[0]), float(item[1])))
            elif isinstance(item, dict) and "lat" in item and "lng" in item:
                pts.append((float(item["lat"]), float(item["lng"])))
        return pts if len(pts) >= 3 else None
    except Exception:
        return None


def point_in_polygon(lat: float, lng: float, polygon: list[tuple[float, float]]) -> bool:
    """Deterministic ray-casting point-in-polygon check."""
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        yi, xi = polygon[i]
        yj, xj = polygon[j]
        intersect = ((yi > lat) != (yj > lat)) and (
            lng < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi
        )
        if intersect:
            inside = not inside
        j = i
    return inside


def list_public_properties(
    *,
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
    amenity_codes: Optional[list[str]] = None,
    q: Optional[str] = None,
    featured_only: bool = False,
    min_lat: Optional[Decimal] = None,
    max_lat: Optional[Decimal] = None,
    min_lng: Optional[Decimal] = None,
    max_lng: Optional[Decimal] = None,
    polygon: Optional[str] = None,
):
    poly_pts = parse_polygon_points(polygon)
    if poly_pts:
        lats = [p[0] for p in poly_pts]
        lngs = [p[1] for p in poly_pts]
        p_min_lat = Decimal(str(min(lats)))
        p_max_lat = Decimal(str(max(lats)))
        p_min_lng = Decimal(str(min(lngs)))
        p_max_lng = Decimal(str(max(lngs)))
        min_lat = max(min_lat, p_min_lat) if min_lat is not None else p_min_lat
        max_lat = min(max_lat, p_max_lat) if max_lat is not None else p_max_lat
        min_lng = max(min_lng, p_min_lng) if min_lng is not None else p_min_lng
        max_lng = min(max_lng, p_max_lng) if max_lng is not None else p_max_lng

    with tenant_bypass():
        qs = (
            Property.objects.all_tenants()
            .filter(
                is_deleted=False,
                status=Property.Status.PUBLISHED,
                visibility=Property.Visibility.PUBLIC_PORTAL,
            )
            .select_related(
                "property_type",
                "deal_type",
                "location",
                "location__province_ref",
                "location__city_ref",
                "location__district_ref",
                "location__neighborhood_ref",
                "agency",
                "currency",
            )
            .prefetch_related(
                "amenities__category",
                "amenity_values__amenity__category",
                "media_items",
                "price_history",
                "status_history",
            )
        )
        if province_id:
            qs = qs.filter(location__province_ref_id=province_id)
        if city_id:
            qs = qs.filter(location__city_ref_id=city_id)
        if district_id:
            qs = qs.filter(location__district_ref_id=district_id)
        if neighborhood_id:
            qs = qs.filter(location__neighborhood_ref_id=neighborhood_id)
        if city:
            qs = qs.filter(location__city__icontains=city)
        if district:
            qs = qs.filter(location__district__icontains=district)
        if deal_type:
            qs = qs.filter(deal_type_id=deal_type)
        if property_type:
            qs = qs.filter(property_type_id=property_type)
        if min_price is not None:
            qs = qs.filter(total_price__gte=min_price)
        if max_price is not None:
            qs = qs.filter(total_price__lte=max_price)
        if min_area is not None:
            qs = qs.filter(built_area_sqm__gte=min_area)
        if max_area is not None:
            qs = qs.filter(built_area_sqm__lte=max_area)
        if min_bedrooms is not None:
            qs = qs.filter(bedrooms__gte=min_bedrooms)
        if featured_only:
            qs = qs.filter(is_featured=True)
        if amenity_codes:
            for code in amenity_codes:
                clean = code.strip().upper()
                if clean:
                    qs = qs.filter(amenities__code=clean)
        if min_lat is not None and max_lat is not None:
            qs = qs.filter(location__latitude__gte=min_lat, location__latitude__lte=max_lat)
        if min_lng is not None and max_lng is not None:
            qs = qs.filter(location__longitude__gte=min_lng, location__longitude__lte=max_lng)
        if q:
            qs = qs.filter(
                models.Q(title__icontains=q)
                | models.Q(property_code__icontains=q)
                | models.Q(location__city__icontains=q)
                | models.Q(location__district__icontains=q)
                | models.Q(location__neighborhood__icontains=q)
            )
        qs = qs.distinct().order_by("-is_featured", "-created_at")

        if poly_pts:
            matching_ids = []
            for p in qs:
                loc = getattr(p, "location", None)
                if loc and loc.latitude is not None and loc.longitude is not None:
                    if point_in_polygon(float(loc.latitude), float(loc.longitude), poly_pts):
                        matching_ids.append(p.id)
            return Property.objects.all_tenants().filter(id__in=matching_ids).select_related(
                "property_type",
                "deal_type",
                "location",
                "location__province_ref",
                "location__city_ref",
                "location__district_ref",
                "location__neighborhood_ref",
                "agency",
                "currency",
            ).prefetch_related(
                "amenities__category",
                "amenity_values__amenity__category",
                "media_items",
                "price_history",
                "status_history",
            ).order_by("-is_featured", "-created_at")

        return qs


def list_agency_properties(
    *,
    user: User,
    agency_id: Optional[UUID],
    status_filter: Optional[str] = None,
    deal_type: Optional[str] = None,
    property_type: Optional[str] = None,
    province_id: Optional[UUID] = None,
    city_id: Optional[UUID] = None,
    district_id: Optional[UUID] = None,
    neighborhood_id: Optional[UUID] = None,
    q: Optional[str] = None,
):
    selects = (
        "property_type",
        "deal_type",
        "location",
        "location__province_ref",
        "location__city_ref",
        "location__district_ref",
        "location__neighborhood_ref",
        "agency",
        "currency",
        "branch",
    )
    prefetches = (
        "amenities__category",
        "amenity_values__amenity__category",
        "media_items",
        "owners__owner_customer",
        "agent_assignments__membership__user",
        "price_history",
        "status_history",
    )
    if is_super_admin(user) and not agency_id:
        qs = (
            Property.objects.all_tenants()
            .filter(is_deleted=False)
            .select_related(*selects)
            .prefetch_related(*prefetches)
        )
    else:
        if not agency_id:
            return Property.objects.none()
        qs = (
            Property.objects.all_tenants()
            .filter(agency_id=agency_id, is_deleted=False)
            .select_related(*selects)
            .prefetch_related(*prefetches)
        )
        if not is_super_admin(user) and not has_agency_permission(user, agency_id, "property.view_all_agency"):
            membership = get_active_membership(user, agency_id)
            if not membership:
                return Property.objects.none()
            policy = get_agency_policy(agency_id)
            if policy.property_view_scope == AgencyAccessPolicy.PropertyViewScope.PUBLIC_AGENCY:
                qs = qs.filter(
                    models.Q(agent_assignments__membership=membership)
                    | models.Q(created_by=user)
                    | models.Q(visibility=Property.Visibility.PUBLIC_PORTAL)
                ).distinct()
            elif policy.property_view_scope == AgencyAccessPolicy.PropertyViewScope.OWN_AND_SHARED:
                qs = qs.filter(
                    models.Q(agent_assignments__membership=membership) | models.Q(created_by=user)
                ).distinct()

    if status_filter:
        qs = qs.filter(status=status_filter)
    if deal_type:
        qs = qs.filter(deal_type_id=deal_type)
    if property_type:
        qs = qs.filter(property_type_id=property_type)
    if province_id:
        qs = qs.filter(location__province_ref_id=province_id)
    if city_id:
        qs = qs.filter(location__city_ref_id=city_id)
    if district_id:
        qs = qs.filter(location__district_ref_id=district_id)
    if neighborhood_id:
        qs = qs.filter(location__neighborhood_ref_id=neighborhood_id)
    if q:
        qs = qs.filter(
            models.Q(title__icontains=q)
            | models.Q(property_code__icontains=q)
            | models.Q(location__district__icontains=q)
            | models.Q(location__city__icontains=q)
            | models.Q(location__neighborhood__icontains=q)
        )
    return qs.order_by("-created_at")


def get_property_for_context(*, user: Optional[User], agency_id: Optional[UUID], property_id: UUID) -> tuple[Property, bool]:
    if user and user.is_authenticated and (agency_id or is_super_admin(user)):
        prop = list_agency_properties(user=user, agency_id=agency_id).filter(id=property_id).first()
        if prop:
            return prop, True
    prop = list_public_properties().filter(id=property_id).first()
    if not prop:
        raise NotFoundDomainError("ملک مورد نظر یافت نشد.")
    return prop, False


def get_property_timeline(*, user: Optional[User], agency_id: Optional[UUID], property_id: UUID) -> list[dict]:
    prop, is_internal = get_property_for_context(user=user, agency_id=agency_id, property_id=property_id)
    events: list[dict] = [
        {
            "id": f"created-{prop.id}",
            "type": "CREATED",
            "title": "ثبت فایل ملک در سامانه",
            "detail": f"کد فایل {prop.property_code}",
            "occurred_at": prop.created_at.isoformat(),
        }
    ]
    for ph in prop.price_history.all().order_by("-changed_at")[:10]:
        events.append({
            "id": f"price-{ph.id}",
            "type": "PRICE_CHANGE",
            "title": "تغییر قیمت ملک",
            "detail": f"از {ph.previous_price} به {ph.new_price} {ph.currency_code}",
            "occurred_at": ph.changed_at.isoformat(),
        })
    for sh in prop.status_history.all().order_by("-changed_at")[:10]:
        events.append({
            "id": f"status-{sh.id}",
            "type": "STATUS_CHANGE",
            "title": f"تغییر وضعیت از {sh.from_status} به {sh.to_status}",
            "detail": sh.reason or "",
            "occurred_at": sh.changed_at.isoformat(),
        })
    if is_internal:
        for ap in ViewingAppointment.objects.all_tenants().filter(property=prop).select_related("customer")[:10]:
            events.append({
                "id": f"visit-{ap.id}",
                "type": "VIEWING",
                "title": f"بازدید ({ap.status})",
                "detail": ap.customer.full_name,
                "occurred_at": ap.scheduled_start.isoformat(),
            })
        for neg in Negotiation.objects.all_tenants().filter(property=prop).select_related("customer")[:10]:
            events.append({
                "id": f"neg-{neg.id}",
                "type": "NEGOTIATION",
                "title": f"مذاکره ({neg.status})",
                "detail": neg.customer.full_name,
                "occurred_at": neg.created_at.isoformat(),
            })
    events.sort(key=lambda e: e["occurred_at"], reverse=True)
    return events


def get_related_properties(*, prop: Property, limit: int = 4) -> list[Property]:
    loc = getattr(prop, "location", None)
    qs = list_public_properties(
        city_id=loc.city_ref_id if loc and loc.city_ref_id else None,
        city=loc.city if (loc and not loc.city_ref_id) else None,
        deal_type=prop.deal_type_id,
    ).exclude(id=prop.id)
    return list(qs[:limit])


def serialize_property_owners(user: User, prop: Property) -> list[dict]:
    if not user or not user.is_authenticated:
        return []
    is_assigned = prop.agent_assignments.filter(membership__user=user).exists()
    if not can_view_owner_pii(user, prop.agency_id, is_assigned):
        return [{"masked": True, "message": "اطلاعات مالک مطابق سیاست آژانس محرمانه است."}]
    return [
        {
            "id": str(o.id),
            "owner_customer_id": str(o.owner_customer_id),
            "full_name": o.owner_customer.full_name,
            "primary_phone": o.owner_customer.primary_phone,
            "ownership_share_percent": str(o.ownership_share_percent),
        }
        for o in prop.owners.select_related("owner_customer").all()
    ]


def _normalize_location_payload(location_data: dict) -> dict:
    payload = dict(location_data)
    prov_id = payload.pop("province_id", None)
    city_id = payload.pop("city_id", None)
    dist_id = payload.pop("district_id", None)
    nbr_id = payload.pop("neighborhood_id", None)

    if any([prov_id, city_id, dist_id, nbr_id]):
        prov, city, dist, nbr = resolve_location_hierarchy(
            province_id=prov_id,
            city_id=city_id,
            district_id=dist_id,
            neighborhood_id=nbr_id,
        )
        if prov:
            payload["province_ref"] = prov
            payload["province"] = prov.name_fa
        if city:
            payload["city_ref"] = city
            payload["city"] = city.name_fa
        if dist:
            payload["district_ref"] = dist
            payload["district"] = dist.name_fa
        elif "district" not in payload:
            payload["district"] = ""
            payload["district_ref"] = None
        if nbr:
            payload["neighborhood_ref"] = nbr
            payload["neighborhood"] = nbr.name_fa
        elif "neighborhood" not in payload:
            payload["neighborhood"] = ""
            payload["neighborhood_ref"] = None

    if not payload.get("city"):
        raise ValidationDomainError("انتخاب شهر برای موقعیت جغرافیایی ملک الزامی است.")
    if not payload.get("province"):
        payload["province"] = "تهران"
    return payload


def _sync_property_amenities(*, prop: Property, amenity_codes: Optional[list[str]], amenity_values: Optional[list[dict]], user: User) -> None:
    codes_set = {c.strip().upper() for c in (amenity_codes or []) if c and c.strip()}
    if amenity_values:
        for item in amenity_values:
            code = str(item.get("code") or "").strip().upper()
            if code:
                codes_set.add(code)

    if amenity_codes is not None or amenity_values is not None:
        amenities_objs = list(Amenity.objects.filter(code__in=codes_set))
        prop.amenities.set(amenities_objs)
        by_code = {a.code: a for a in amenities_objs}

        if amenity_values is not None:
            PropertyAmenityValue.objects.filter(property=prop).exclude(amenity__code__in=codes_set).delete()
            for item in amenity_values:
                code = str(item.get("code") or "").strip().upper()
                am = by_code.get(code)
                if not am:
                    continue
                val_num = item.get("value_number")
                PropertyAmenityValue.objects.update_or_create(
                    property=prop,
                    amenity=am,
                    defaults={
                        "value_text": str(item.get("value_text") or "").strip(),
                        "value_number": Decimal(str(val_num)) if val_num not in (None, "") else None,
                        "updated_by": user,
                        "created_by": user,
                    },
                )


@transaction.atomic
def create_property(*, user: User, agency_id: UUID, data: dict) -> Property:
    membership = get_active_membership(user, agency_id)
    if not membership and not is_super_admin(user):
        raise PermissionDeniedDomainError("برای ثبت ملک باید عضو فعال یک آژانس باشید.")

    if Property.objects.all_tenants().filter(agency_id=agency_id, property_code=data["property_code"]).exists():
        raise ConflictDomainError("کد فایل ملک در این آژانس تکراری است.")

    location_data = data.pop("location", None)
    amenity_codes = data.pop("amenity_codes", [])
    amenity_values = data.pop("amenity_values", [])
    owner_customer_id = data.pop("owner_customer_id", None)
    initial_media_url = data.pop("initial_media_url", None)

    prop = Property(
        agency_id=agency_id,
        branch_id=data.get("branch_id") or (membership.branch_id if membership else None),
        property_code=data["property_code"],
        title=data["title"],
        description=data.get("description", ""),
        property_type_id=data["property_type_id"],
        deal_type_id=data["deal_type_id"],
        usage_type=data.get("usage_type", "مسکونی"),
        visibility=data.get("visibility", Property.Visibility.PRIVATE_AGENCY),
        is_featured=bool(data.get("is_featured", False)),
        land_area_sqm=Decimal(data.get("land_area_sqm", "0")),
        built_area_sqm=Decimal(data.get("built_area_sqm", "0")),
        bedrooms=int(data.get("bedrooms", 0)),
        bathrooms=int(data.get("bathrooms", 0)),
        floor_number=data.get("floor_number"),
        total_floors=data.get("total_floors"),
        units_per_floor=data.get("units_per_floor"),
        building_age=data.get("building_age"),
        construction_year=data.get("construction_year"),
        deed_type=data.get("deed_type", "تک‌برگ"),
        deed_status=data.get("deed_status", "آزاد"),
        orientation=data.get("orientation", ""),
        facade_type=data.get("facade_type", ""),
        currency_id=data.get("currency_id", "IRT"),
        total_price=Decimal(data.get("total_price", "0")),
        deposit_amount=Decimal(data.get("deposit_amount", "0")),
        rent_amount=Decimal(data.get("rent_amount", "0")),
        min_acceptable_price=Decimal(data["min_acceptable_price"]) if data.get("min_acceptable_price") is not None else None,
        is_negotiable=bool(data.get("is_negotiable", True)),
        is_exclusive=bool(data.get("is_exclusive", False)),
        created_by=user,
    )
    prop.recalculate_price_per_sqm()
    prop.save()

    _sync_property_amenities(prop=prop, amenity_codes=amenity_codes, amenity_values=amenity_values, user=user)

    if location_data:
        loc_payload = _normalize_location_payload(location_data)
        PropertyLocation.objects.create(property=prop, **loc_payload)

    if owner_customer_id:
        PropertyOwner.objects.create(
            property=prop,
            owner_customer_id=owner_customer_id,
            created_by=user,
        )

    if membership:
        PropertyAgentAssignment.objects.create(
            property=prop,
            membership=membership,
            role=PropertyAgentAssignment.Role.PRIMARY,
            created_by=user,
        )

    if initial_media_url:
        PropertyMedia.objects.create(
            property=prop,
            url=initial_media_url,
            title=prop.title,
            is_cover=True,
            is_public=True,
            created_by=user,
        )

    record_audit_event(
        action="PROPERTY_CREATED",
        resource_type="Property",
        resource_id=str(prop.id),
        actor=user,
        agency_id=agency_id,
    )
    return prop


@transaction.atomic
def update_property(*, user: User, agency_id: UUID, property_id: UUID, data: dict) -> Property:
    prop = Property.objects.all_tenants().filter(id=property_id, agency_id=agency_id, is_deleted=False).first()
    if not prop:
        raise NotFoundDomainError("ملک یافت نشد.")
    if not can_edit_property(user, prop):
        raise PermissionDeniedDomainError("شما مجوز ویرایش این ملک را ندارید.")

    prev_price = prop.total_price
    location_data = data.pop("location", None)
    amenity_codes = data.pop("amenity_codes", None)
    amenity_values = data.pop("amenity_values", None)

    updatable = [
        "title", "description", "property_type_id", "deal_type_id", "usage_type", "visibility",
        "is_featured", "land_area_sqm", "built_area_sqm", "bedrooms", "bathrooms",
        "floor_number", "total_floors", "units_per_floor", "building_age", "construction_year",
        "deed_type", "deed_status", "orientation", "facade_type", "currency_id",
        "total_price", "deposit_amount", "rent_amount", "min_acceptable_price",
        "is_negotiable", "is_exclusive", "branch_id",
    ]
    for k in updatable:
        if k in data and data[k] is not None:
            setattr(prop, k, data[k])
    prop.updated_by = user
    prop.recalculate_price_per_sqm()
    prop.save()

    if prop.total_price != prev_price:
        PropertyPriceHistory.objects.create(
            property=prop,
            previous_price=prev_price,
            new_price=prop.total_price,
            currency_code=prop.currency_id,
            changed_by=user,
        )

    if amenity_codes is not None or amenity_values is not None:
        _sync_property_amenities(prop=prop, amenity_codes=amenity_codes, amenity_values=amenity_values, user=user)

    if location_data is not None:
        loc_payload = _normalize_location_payload(location_data)
        PropertyLocation.objects.update_or_create(property=prop, defaults=loc_payload)

    record_audit_event(
        action="PROPERTY_UPDATED",
        resource_type="Property",
        resource_id=str(prop.id),
        actor=user,
        agency_id=agency_id,
    )
    return prop


@transaction.atomic
def soft_delete_property(*, user: User, agency_id: UUID, property_id: UUID) -> None:
    prop = Property.objects.all_tenants().filter(id=property_id, agency_id=agency_id, is_deleted=False).first()
    if not prop:
        raise NotFoundDomainError("ملک یافت نشد.")
    if not can_edit_property(user, prop):
        raise PermissionDeniedDomainError("شما مجوز حذف این ملک را ندارید.")
    prop.soft_delete(user=user)
    record_audit_event(
        action="PROPERTY_SOFT_DELETED",
        resource_type="Property",
        resource_id=str(prop.id),
        actor=user,
        agency_id=agency_id,
    )


@transaction.atomic
def transition_property_status(
    *, user: User, agency_id: UUID, property_id: UUID, to_status: str, reason: str = ""
) -> Property:
    prop = Property.objects.all_tenants().filter(id=property_id, agency_id=agency_id, is_deleted=False).first()
    if not prop:
        raise NotFoundDomainError("ملک یافت نشد.")
    if to_status == Property.Status.PUBLISHED and not (
        is_super_admin(user) or has_agency_permission(user, agency_id, "property.publish")
    ):
        raise PermissionDeniedDomainError("عدم مجوز انتشار عمومی ملک.")
    elif not can_edit_property(user, prop) and not has_agency_permission(user, agency_id, "property.publish"):
        raise PermissionDeniedDomainError("عدم مجوز تغییر وضعیت ملک.")

    prev = prop.status
    prop.status = to_status
    if to_status == Property.Status.PUBLISHED:
        prop.visibility = Property.Visibility.PUBLIC_PORTAL
    prop.updated_by = user
    prop.save(update_fields=["status", "visibility", "updated_by", "updated_at"])
    PropertyStatusHistory.objects.create(
        property=prop,
        from_status=prev,
        to_status=to_status,
        reason=reason,
        changed_by=user,
    )
    record_audit_event(
        action=f"PROPERTY_STATUS_{to_status}",
        resource_type="Property",
        resource_id=str(prop.id),
        actor=user,
        agency_id=agency_id,
        before_state={"status": prev},
        after_state={"status": to_status},
    )
    return prop


@transaction.atomic
def add_property_media(
    *, user: User, agency_id: UUID, property_id: UUID, media_type: str, url: str, title: str = "", is_cover: bool = False, is_public: bool = True
) -> PropertyMedia:
    prop = Property.objects.all_tenants().filter(id=property_id, agency_id=agency_id, is_deleted=False).first()
    if not prop:
        raise NotFoundDomainError("ملک یافت نشد.")
    if not can_edit_property(user, prop):
        raise PermissionDeniedDomainError("عدم مجوز افزودن رسانه به این ملک.")
    if is_cover:
        PropertyMedia.objects.filter(property=prop).update(is_cover=False)
    next_sort = PropertyMedia.objects.filter(property=prop).count() + 1
    media = PropertyMedia.objects.create(
        property=prop,
        media_type=media_type,
        url=url,
        title=title,
        is_cover=is_cover,
        is_public=is_public,
        sort_order=next_sort,
        created_by=user,
    )
    return media


@transaction.atomic
def upload_property_media_file(
    *,
    user: User,
    agency_id: UUID,
    property_id: UUID,
    filename: str,
    content_type: str,
    content: bytes,
    title: str = "",
    is_cover: bool = False,
    is_public: bool = True,
) -> PropertyMedia:
    prop = Property.objects.all_tenants().filter(id=property_id, agency_id=agency_id, is_deleted=False).first()
    if not prop:
        raise NotFoundDomainError("ملک یافت نشد.")
    if not can_edit_property(user, prop):
        raise PermissionDeniedDomainError("عدم مجوز بارگذاری تصویر برای این ملک.")
    safe_name, verified_mime = validate_uploaded_file(
        filename=filename, content_type=content_type, content=content
    )
    storage = get_storage_provider()
    stored = storage.put_bytes(
        key_prefix=f"agencies/{agency_id}/properties/{property_id}",
        safe_filename=safe_name,
        content=content,
        mime_type=verified_mime,
    )
    if is_cover:
        PropertyMedia.objects.filter(property=prop).update(is_cover=False)
    next_sort = PropertyMedia.objects.filter(property=prop).count() + 1
    return PropertyMedia.objects.create(
        property=prop,
        media_type="IMAGE" if verified_mime.startswith("image/") else "DOCUMENT",
        file_key=stored.file_key,
        url=stored.url,
        title=title or safe_name or prop.title,
        is_cover=is_cover,
        is_public=is_public,
        sort_order=next_sort,
        created_by=user,
    )


@transaction.atomic
def reorder_property_media(
    *, user: User, agency_id: UUID, property_id: UUID, ordered_media_ids: list[UUID], cover_media_id: Optional[UUID] = None
) -> list[PropertyMedia]:
    prop = Property.objects.all_tenants().filter(id=property_id, agency_id=agency_id, is_deleted=False).first()
    if not prop:
        raise NotFoundDomainError("ملک یافت نشد.")
    if not can_edit_property(user, prop):
        raise PermissionDeniedDomainError("عدم مجوز مرتب‌سازی رسانه‌های ملک.")
    for idx, mid in enumerate(ordered_media_ids, start=1):
        PropertyMedia.objects.filter(property=prop, id=mid).update(sort_order=idx)
    if cover_media_id:
        PropertyMedia.objects.filter(property=prop).update(is_cover=False)
        PropertyMedia.objects.filter(property=prop, id=cover_media_id).update(is_cover=True)
    return list(PropertyMedia.objects.filter(property=prop).order_by("sort_order", "created_at"))


@transaction.atomic
def delete_property_media(*, user: User, agency_id: UUID, property_id: UUID, media_id: UUID) -> None:
    prop = Property.objects.all_tenants().filter(id=property_id, agency_id=agency_id, is_deleted=False).first()
    if not prop:
        raise NotFoundDomainError("ملک یافت نشد.")
    if not can_edit_property(user, prop):
        raise PermissionDeniedDomainError("عدم مجوز حذف رسانه.")
    deleted, _ = PropertyMedia.objects.filter(id=media_id, property=prop).delete()
    if not deleted:
        raise NotFoundDomainError("فایل رسانه یافت نشد.")
