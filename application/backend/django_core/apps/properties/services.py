from decimal import Decimal
import json
from typing import Optional
from uuid import UUID
from django.db import models, transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.agencies.models import AgencyAccessPolicy
from apps.appointments.models import ViewingAppointment
from apps.audit.services import record_audit_event
from apps.documents.models import Document
from apps.negotiations.models import Negotiation
from apps.property_media.models import PropertyMedia
from apps.settings.services import get_setting_value, resolve_location_hierarchy
from common.exceptions import ConflictDomainError, NotFoundDomainError, PermissionDeniedDomainError, ValidationDomainError
from common.permissions import (
    can_edit_property,
    can_view_property,
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
    PropertyVerification,
    PropertyVerificationHistory,
    PropertyViolationReport,
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

    with tenant_bypass(reason="public_catalog"): 
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
                "verification",
            )
            .prefetch_related(
                "amenities__category",
                "amenity_values__amenity__category",
                "media_items",
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
        "verification",
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
    if not agency_id:
        return Property.objects.all_tenants().none()
    qs = (
        Property.objects.all_tenants()
        .filter(agency_id=agency_id, is_deleted=False)
        .select_related(*selects)
        .prefetch_related(*prefetches)
    )
    if not is_super_admin(user):
        membership = get_active_membership(user, agency_id)
        if not membership:
            return Property.objects.all_tenants().none()
        if membership.role.code == "BRANCH_MANAGER":
            if not membership.branch_id:
                return Property.objects.all_tenants().none()
            qs = qs.filter(branch_id=membership.branch_id)
        elif not has_agency_permission(user, agency_id, "property.view_all_agency"):
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
    if user and user.is_authenticated and is_super_admin(user):
        if agency_id:
            prop = Property.objects.all_tenants().filter(id=property_id, agency_id=agency_id, is_deleted=False).first()
        else:
            with tenant_bypass(reason="platform_reports"):
                prop = Property.objects.all_tenants().filter(id=property_id, is_deleted=False).first()
        if prop:
            return prop, True
    if user and user.is_authenticated and agency_id:
        prop = list_agency_properties(user=user, agency_id=agency_id).filter(id=property_id).first()
        if prop:
            return prop, True
    with tenant_bypass(reason="public_catalog"):
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
    if is_internal:
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
    with tenant_bypass(reason="public_catalog"):
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


def _resolve_editable_property(*, user: User, agency_id: Optional[UUID], property_id: UUID) -> Property:
    qs = Property.objects.all_tenants().filter(id=property_id, is_deleted=False)
    if agency_id:
        qs = qs.filter(agency_id=agency_id)
    elif not is_super_admin(user):
        raise PermissionDeniedDomainError("ابتدا آژانس را انتخاب کنید.")
    prop = qs.first()
    if not prop:
        raise NotFoundDomainError("ملک یافت نشد.")
    return prop


@transaction.atomic
def create_property(*, user: User, agency_id: Optional[UUID], data: dict) -> Property:
    if not agency_id:
        raise ValidationDomainError("ابتدا آژانس فعال را انتخاب کنید.")
    membership = get_active_membership(user, agency_id)
    if not membership and not is_super_admin(user):
        raise PermissionDeniedDomainError("برای ثبت ملک باید عضو فعال یک آژانس باشید.")
    if not (is_super_admin(user) or has_agency_permission(user, agency_id, "property.create")):
        raise PermissionDeniedDomainError("مجوز ثبت ملک را ندارید.")
    requested_branch_id = data.get("branch_id") or (membership.branch_id if membership else None)
    if requested_branch_id:
        from apps.branches.models import Branch
        if not Branch.objects.filter(id=requested_branch_id, agency_id=agency_id, is_active=True).exists():
            raise ValidationDomainError("شعبه انتخاب‌شده متعلق به این آژانس نیست یا فعال نیست.")
    if membership and membership.role.code == "BRANCH_MANAGER":
        if not membership.branch_id or requested_branch_id != membership.branch_id:
            raise PermissionDeniedDomainError("مدیر شعبه فقط می‌تواند در شعبه خودش ملک ثبت کند.")
    elif membership and not has_agency_permission(user, agency_id, "property.view_all_agency"):
        if requested_branch_id != membership.branch_id:
            raise PermissionDeniedDomainError("ثبت ملک خارج از شعبه تخصیص‌یافته مجاز نیست.")
    if data.get("visibility") == Property.Visibility.PUBLIC_PORTAL or data.get("is_featured"):
        if not has_agency_permission(user, agency_id, "property.publish"):
            raise PermissionDeniedDomainError("مجوز انتشار یا ویژه‌سازی ملک را ندارید.")

    if Property.objects.all_tenants().filter(agency_id=agency_id, property_code=data["property_code"]).exists():
        raise ConflictDomainError("کد فایل ملک در این آژانس تکراری است.")

    from apps.subscriptions.services import enforce_agency_quota

    active_listings_count = (
        Property.objects.all_tenants()
        .filter(agency_id=agency_id, is_deleted=False)
        .exclude(status__in=[Property.Status.ARCHIVED, Property.Status.REJECTED])
        .count()
    )
    enforce_agency_quota(
        agency_id=agency_id,
        quota_field="max_active_listings",
        current_count=active_listings_count,
        actor=user,
        label_fa="فایل‌های ملکی فعال",
    )

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
        from apps.customers.models import Customer
        if not Customer.objects.all_tenants().filter(
            id=owner_customer_id, agency_id=agency_id, is_deleted=False
        ).exists():
            raise ValidationDomainError("مالک ملک باید مشتری همین آژانس باشد.")
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
def update_property(*, user: User, agency_id: Optional[UUID], property_id: UUID, data: dict) -> Property:
    prop = _resolve_editable_property(user=user, agency_id=agency_id, property_id=property_id)
    if not can_edit_property(user, prop):
        raise PermissionDeniedDomainError("شما مجوز ویرایش این ملک را ندارید.")

    prev_price = prop.total_price
    prev_rent_amount = prop.rent_amount
    if "branch_id" in data and data["branch_id"] is not None:
        from apps.branches.models import Branch
        if not Branch.objects.filter(id=data["branch_id"], agency_id=prop.agency_id, is_active=True).exists():
            raise ValidationDomainError("شعبه انتخاب‌شده متعلق به این آژانس نیست یا فعال نیست.")
        membership = get_active_membership(user, prop.agency_id)
        if membership and membership.role.code == "BRANCH_MANAGER" and data["branch_id"] != membership.branch_id:
            raise PermissionDeniedDomainError("انتقال ملک به شعبه دیگر مجاز نیست.")
        if membership and not has_agency_permission(user, prop.agency_id, "property.view_all_agency") and data["branch_id"] != membership.branch_id:
            raise PermissionDeniedDomainError("انتقال ملک خارج از شعبه تخصیص‌یافته مجاز نیست.")
    if data.get("visibility") == Property.Visibility.PUBLIC_PORTAL or data.get("is_featured") is True:
        if not has_agency_permission(user, prop.agency_id, "property.publish"):
            raise PermissionDeniedDomainError("مجوز انتشار یا ویژه‌سازی ملک را ندارید.")
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
    if (
        data.get("visibility") == Property.Visibility.PUBLIC_PORTAL
        and prop.status == Property.Status.PUBLISHED
    ):
        _assert_property_verified_for_public_publish(prop)
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
    if prop.rent_amount != prev_rent_amount:
        PropertyPriceHistory.objects.create(
            property=prop,
            previous_price=prev_rent_amount,
            new_price=prop.rent_amount,
            currency_code=f"RENT:{prop.currency_id}",
            changed_by=user,
        )
    if prop.total_price != prev_price or prop.rent_amount != prev_rent_amount:
        # Phase 4 saved-search price alerts are best-effort; notification failures
        # never invalidate the property price update.
        try:
            from apps.search.phase4 import notify_saved_search_price_change
            notify_saved_search_price_change(prop, actor=user)
        except Exception:
            pass

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
        agency_id=prop.agency_id,
    )
    return prop


@transaction.atomic
def soft_delete_property(*, user: User, agency_id: Optional[UUID], property_id: UUID) -> None:
    prop = _resolve_editable_property(user=user, agency_id=agency_id, property_id=property_id)
    if not can_edit_property(user, prop):
        raise PermissionDeniedDomainError("شما مجوز حذف این ملک را ندارید.")
    prop.soft_delete(user=user)
    record_audit_event(
        action="PROPERTY_SOFT_DELETED",
        resource_type="Property",
        resource_id=str(prop.id),
        actor=user,
        agency_id=prop.agency_id,
    )


def _assert_property_verified_for_public_publish(prop: Property) -> None:
    require_gate = bool(get_setting_value("compliance.require_property_verification_before_publish", True))
    if not require_gate:
        return
    ver = PropertyVerification.objects.filter(property=prop).first()
    if not ver or ver.verification_status not in (
        PropertyVerification.VerificationStatus.VERIFIED,
        PropertyVerification.VerificationStatus.EXCEPTION_APPROVED,
    ):
        raise ValidationDomainError(
            "مطابق مقررات احراز اصالت فایل‌های ملکی، پیش از انتشار عمومی باید وجود فیزیکی ملک، بررسی سند و رضایت مالک تأیید شوند یا استثنای مجاز با ثبت دلیل صادر گردد."
        )
    if ver.verification_status == PropertyVerification.VerificationStatus.VERIFIED:
        if bool(get_setting_value("compliance.require_physical_verification", True)) and not ver.physical_verified:
            raise ValidationDomainError("تأیید وجود فیزیکی ملک پیش از انتشار الزامی است.")
        if bool(get_setting_value("compliance.require_deed_verification", True)) and not ver.deed_verified:
            raise ValidationDomainError("تأیید بررسی سند ملک پیش از انتشار الزامی است.")
        if bool(get_setting_value("compliance.require_owner_consent", True)) and not ver.owner_consent_verified:
            raise ValidationDomainError("تأیید رضایت مالک پیش از انتشار الزامی است.")


@transaction.atomic
def transition_property_status(
    *, user: User, agency_id: Optional[UUID], property_id: UUID, to_status: str, reason: str = ""
) -> Property:
    valid_statuses = {c[0] for c in Property.Status.choices}
    if to_status not in valid_statuses:
        raise ValidationDomainError(f"وضعیت «{to_status}» برای ملک معتبر نیست.")
    prop = _resolve_editable_property(user=user, agency_id=agency_id, property_id=property_id)
    eff_agency_id = prop.agency_id
    if to_status == Property.Status.PUBLISHED and not (
        is_super_admin(user) or has_agency_permission(user, eff_agency_id, "property.publish")
    ):
        raise PermissionDeniedDomainError("عدم مجوز انتشار عمومی ملک.")
    elif not can_edit_property(user, prop) and not has_agency_permission(user, eff_agency_id, "property.publish"):
        raise PermissionDeniedDomainError("عدم مجوز تغییر وضعیت ملک.")

    if to_status == Property.Status.REJECTED and not (reason or "").strip():
        raise ValidationDomainError("برای رد ملک، درج دلیل رد الزامی است.")

    if to_status == Property.Status.PUBLISHED:
        _assert_property_verified_for_public_publish(prop)

    prev = prop.status
    prop.status = to_status
    if to_status == Property.Status.PUBLISHED:
        prop.visibility = Property.Visibility.PUBLIC_PORTAL
    elif to_status in (
        Property.Status.DRAFT,
        Property.Status.INACTIVE,
        Property.Status.REJECTED,
        Property.Status.ARCHIVED,
    ):
        prop.visibility = Property.Visibility.PRIVATE_AGENCY
    prop.updated_by = user
    prop.save(update_fields=["status", "visibility", "updated_by", "updated_at"])
    PropertyStatusHistory.objects.create(
        property=prop,
        from_status=prev,
        to_status=to_status,
        reason=(reason or "").strip(),
        changed_by=user,
    )
    record_audit_event(
        action=f"PROPERTY_STATUS_{to_status}",
        resource_type="Property",
        resource_id=str(prop.id),
        actor=user,
        agency_id=eff_agency_id,
        before_state={"status": prev},
        after_state={"status": to_status, "reason": (reason or "").strip()},
    )
    return prop


@transaction.atomic
def add_property_media(
    *, user: User, agency_id: Optional[UUID], property_id: UUID, media_type: str, url: str, title: str = "", is_cover: bool = False, is_public: bool = True
) -> PropertyMedia:
    prop = _resolve_editable_property(user=user, agency_id=agency_id, property_id=property_id)
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
    agency_id: Optional[UUID],
    property_id: UUID,
    filename: str,
    content_type: str,
    content: bytes,
    title: str = "",
    is_cover: bool = False,
    is_public: bool = True,
) -> PropertyMedia:
    prop = _resolve_editable_property(user=user, agency_id=agency_id, property_id=property_id)
    if not can_edit_property(user, prop):
        raise PermissionDeniedDomainError("عدم مجوز بارگذاری تصویر برای این ملک.")
    safe_name, verified_mime = validate_uploaded_file(
        filename=filename, content_type=content_type, content=content
    )
    storage = get_storage_provider()
    stored = storage.put_bytes(
        key_prefix=f"private/agencies/{prop.agency_id}/properties/{property_id}",
        safe_filename=safe_name,
        content=content,
        mime_type=verified_mime,
    )
    if is_cover:
        PropertyMedia.objects.filter(property=prop).update(is_cover=False)
    next_sort = PropertyMedia.objects.filter(property=prop).count() + 1
    media = PropertyMedia.objects.create(
        property=prop,
        media_type="IMAGE" if verified_mime.startswith("image/") else "DOCUMENT",
        file_key=stored.file_key,
        url="",
        title=title or safe_name or prop.title,
        is_cover=is_cover,
        is_public=is_public,
        sort_order=next_sort,
        created_by=user,
    )
    media.url = f"/api/v1/properties/{prop.id}/media/{media.id}/file"
    media.save(update_fields=["url", "updated_at"])
    return media


def get_property_media_file(*, user: Optional[User], agency_id: Optional[UUID], property_id: UUID, media_id: UUID):
    from apps.property_media.models import PropertyMedia
    if user and is_super_admin(user):
        with tenant_bypass(reason="platform_reports"):
            prop = Property.objects.all_tenants().filter(id=property_id, is_deleted=False).first()
            media = PropertyMedia.objects.filter(id=media_id, property=prop).first() if prop else None
    elif user and agency_id:
        prop = list_agency_properties(user=user, agency_id=agency_id).filter(id=property_id).first()
        media = PropertyMedia.objects.filter(id=media_id, property=prop).first() if prop else None
    else:
        with tenant_bypass(reason="public_catalog"):
            prop = Property.objects.all_tenants().filter(
                id=property_id, is_deleted=False, status=Property.Status.PUBLISHED,
                visibility=Property.Visibility.PUBLIC_PORTAL,
            ).first()
            media = PropertyMedia.objects.filter(id=media_id, property=prop).first() if prop else None
    if not prop:
        raise NotFoundDomainError("ملک یافت نشد یا دسترسی به رسانه آن مجاز نیست.")
    if not media or not media.file_key:
        raise NotFoundDomainError("فایل رسانه یافت نشد.")
    is_public_listing = (
        prop.status == Property.Status.PUBLISHED
        and prop.visibility == Property.Visibility.PUBLIC_PORTAL
        and media.is_public
    )
    if not is_public_listing and not (
        user and (agency_id or is_super_admin(user))
    ):
        raise PermissionDeniedDomainError("دسترسی عمومی به این رسانه مجاز نیست.")
    storage = get_storage_provider()
    try:
        content = storage.get_bytes(file_key=media.file_key)
    except FileNotFoundError as exc:
        raise NotFoundDomainError("فایل رسانه در مخزن یافت نشد.") from exc
    import mimetypes
    mime_type = mimetypes.guess_type(media.file_key)[0] or (
        "image/jpeg" if media.media_type == "IMAGE" else "application/octet-stream"
    )
    if not is_public_listing and user:
        record_audit_event(
            action="PRIVATE_PROPERTY_MEDIA_DOWNLOADED",
            resource_type="PropertyMedia",
            resource_id=str(media.id),
            actor=user,
            agency_id=prop.agency_id,
        )
    return content, mime_type, media.title or f"property-{property_id}-media-{media_id}"


@transaction.atomic
def reorder_property_media(
    *, user: User, agency_id: Optional[UUID], property_id: UUID, ordered_media_ids: list[UUID], cover_media_id: Optional[UUID] = None
) -> list[PropertyMedia]:
    prop = _resolve_editable_property(user=user, agency_id=agency_id, property_id=property_id)
    if not can_edit_property(user, prop):
        raise PermissionDeniedDomainError("عدم مجوز مرتب‌سازی رسانه‌های ملک.")
    for idx, mid in enumerate(ordered_media_ids, start=1):
        PropertyMedia.objects.filter(property=prop, id=mid).update(sort_order=idx)
    if cover_media_id:
        PropertyMedia.objects.filter(property=prop).update(is_cover=False)
        PropertyMedia.objects.filter(property=prop, id=cover_media_id).update(is_cover=True)
    return list(PropertyMedia.objects.filter(property=prop).order_by("sort_order", "created_at"))


@transaction.atomic
def delete_property_media(*, user: User, agency_id: Optional[UUID], property_id: UUID, media_id: UUID) -> None:
    prop = _resolve_editable_property(user=user, agency_id=agency_id, property_id=property_id)
    if not can_edit_property(user, prop):
        raise PermissionDeniedDomainError("عدم مجوز حذف رسانه.")
    deleted, _ = PropertyMedia.objects.filter(id=media_id, property=prop).delete()
    if not deleted:
        raise NotFoundDomainError("فایل رسانه یافت نشد.")


# ==============================================================================
# Property Authenticity Verification, Anomaly Detection & Violation Reports
# ==============================================================================


def detect_property_anomalies(prop: Property) -> list[dict]:
    flags: list[dict] = []
    if not bool(get_setting_value("compliance.enable_duplicate_and_price_anomaly_detection", True)):
        return flags

    with tenant_bypass(reason="compliance_duplicate_detection"): 
        if prop.deal_type_id == "SALE" and prop.total_price > Decimal("0") and prop.total_price < Decimal("50000000"):
            flags.append({
                "code": "SUSPICIOUS_LOW_PRICE",
                "severity": "HIGH",
                "message": "قیمت کل آگهی فروش به‌طور غیرمعمول پایین ثبت شده است و نیازمند بازبینی است.",
            })

        loc = getattr(prop, "location", None)
        if loc and prop.price_per_sqm and prop.price_per_sqm > Decimal("0") and loc.city:
            peers_avg = (
                Property.objects.all_tenants()
                .filter(
                    is_deleted=False,
                    status=Property.Status.PUBLISHED,
                    deal_type_id=prop.deal_type_id,
                    property_type_id=prop.property_type_id,
                    location__city=loc.city,
                    price_per_sqm__gt=Decimal("0"),
                )
                .exclude(id=prop.id)
                .aggregate(avg_pps=models.Avg("price_per_sqm"), cnt=models.Count("id"))
            )
            cnt = int(peers_avg.get("cnt") or 0)
            avg_pps = peers_avg.get("avg_pps")
            if cnt >= 2 and avg_pps and Decimal(avg_pps) > Decimal("0"):
                avg_dec = Decimal(avg_pps)
                if prop.price_per_sqm < avg_dec * Decimal("0.30") or prop.price_per_sqm > avg_dec * Decimal("3.20"):
                    flags.append({
                        "code": "FAKE_PRICE_ANOMALY",
                        "severity": "MEDIUM",
                        "message": f"قیمت هر مترمربع این ملک اختلاف قابل‌توجهی با میانگین شهر {loc.city} دارد.",
                    })

        if loc:
            dup_qs = Property.objects.all_tenants().filter(
                is_deleted=False,
                deal_type_id=prop.deal_type_id,
                property_type_id=prop.property_type_id,
            ).exclude(id=prop.id).exclude(status__in=[Property.Status.ARCHIVED, Property.Status.REJECTED])

            if loc.postal_code and loc.postal_code.strip():
                if dup_qs.filter(location__postal_code=loc.postal_code.strip()).exists():
                    flags.append({
                        "code": "DUPLICATE_POSTAL_CODE",
                        "severity": "HIGH",
                        "message": "ملک فعال دیگری با همین کد پستی در سامانه ثبت شده است.",
                    })
            elif loc.latitude is not None and loc.longitude is not None and prop.built_area_sqm > Decimal("0"):
                eps = Decimal("0.00025")
                area_low = prop.built_area_sqm * Decimal("0.95")
                area_high = prop.built_area_sqm * Decimal("1.05")
                if dup_qs.filter(
                    location__latitude__range=(loc.latitude - eps, loc.latitude + eps),
                    location__longitude__range=(loc.longitude - eps, loc.longitude + eps),
                    built_area_sqm__range=(area_low, area_high),
                ).exists():
                    flags.append({
                        "code": "DUPLICATE_LISTING_SUSPECTED",
                        "severity": "MEDIUM",
                        "message": "آگهی مشابهی با مختصات و متراژ یکسان در سامانه یافت شد.",
                    })
    return flags


def get_property_verification(*, user: User, agency_id: Optional[UUID], property_id: UUID) -> dict:
    qs = Property.objects.all_tenants().filter(id=property_id, is_deleted=False).select_related("location")
    if not is_super_admin(user):
        if not agency_id:
            raise PermissionDeniedDomainError("دسترسی به پرونده احراز اصالت ملک مجاز نیست.")
        qs = qs.filter(agency_id=agency_id)
    prop = qs.first()
    if not prop:
        raise NotFoundDomainError("ملک یافت نشد.")
    if not is_super_admin(user) and not can_view_property(user, prop):
        raise PermissionDeniedDomainError("دسترسی به پرونده احراز اصالت این ملک مجاز نیست.")

    ver = PropertyVerification.objects.select_related(
        "verified_by", "override_by", "evidence_document"
    ).prefetch_related("history__changed_by").filter(property=prop).first()
    anomalies = detect_property_anomalies(prop)

    if not ver:
        return {
            "property_id": str(prop.id),
            "physical_verified": False,
            "physical_notes": "",
            "deed_verified": False,
            "deed_notes": "",
            "owner_consent_verified": False,
            "owner_consent_notes": "",
            "verification_status": PropertyVerification.VerificationStatus.UNVERIFIED,
            "verified_by_name": None,
            "verified_at": None,
            "evidence_document_id": None,
            "evidence_document_title": None,
            "exception_override": False,
            "override_reason": "",
            "override_by_name": None,
            "history": [],
            "anomaly_flags": anomalies,
        }

    return {
        "id": str(ver.id),
        "property_id": str(prop.id),
        "physical_verified": ver.physical_verified,
        "physical_notes": ver.physical_notes,
        "deed_verified": ver.deed_verified,
        "deed_notes": ver.deed_notes,
        "owner_consent_verified": ver.owner_consent_verified,
        "owner_consent_notes": ver.owner_consent_notes,
        "verification_status": ver.verification_status,
        "verified_by_name": ver.verified_by.full_name if ver.verified_by else None,
        "verified_at": ver.verified_at.isoformat() if ver.verified_at else None,
        "evidence_document_id": str(ver.evidence_document_id) if ver.evidence_document_id else None,
        "evidence_document_title": ver.evidence_document.title if ver.evidence_document else None,
        "exception_override": ver.exception_override,
        "override_reason": ver.override_reason,
        "override_by_name": ver.override_by.full_name if ver.override_by else None,
        "history": [
            {
                "id": str(h.id),
                "from_status": h.from_status,
                "to_status": h.to_status,
                "notes": h.notes,
                "changed_by_name": h.changed_by.full_name if h.changed_by else "سیستم",
                "created_at": h.created_at.isoformat(),
            }
            for h in ver.history.all()[:20]
        ],
        "anomaly_flags": anomalies,
    }


@transaction.atomic
def upsert_property_verification(
    *, user: User, agency_id: Optional[UUID], property_id: UUID, data: dict
) -> dict:
    qs = Property.objects.all_tenants().filter(id=property_id, is_deleted=False)
    if not is_super_admin(user):
        if not agency_id:
            raise PermissionDeniedDomainError("دسترسی مجاز نیست.")
        qs = qs.filter(agency_id=agency_id)
    prop = qs.first()
    if not prop:
        raise NotFoundDomainError("ملک یافت نشد.")

    can_review = is_super_admin(user) or has_agency_permission(user, prop.agency_id, "property.publish") or has_agency_permission(user, prop.agency_id, "agency.manage_policy")
    can_override = is_super_admin(user) or has_agency_permission(user, prop.agency_id, "agency.manage_policy")
    if not can_review and not can_edit_property(user, prop):
        raise PermissionDeniedDomainError("شما مجوز ثبت یا بررسی اصالت این ملک را ندارید.")

    ver, _ = PropertyVerification.objects.get_or_create(
        property=prop,
        defaults={"created_by": user},
    )
    prev_status = ver.verification_status

    for bool_field in ("physical_verified", "deed_verified", "owner_consent_verified"):
        if bool_field in data and data[bool_field] is not None:
            setattr(ver, bool_field, bool(data[bool_field]))
    for text_field in ("physical_notes", "deed_notes", "owner_consent_notes"):
        if text_field in data and data[text_field] is not None:
            setattr(ver, text_field, str(data[text_field]).strip()[:255])

    if "evidence_document_id" in data:
        doc_id = data["evidence_document_id"]
        if doc_id:
            doc = Document.objects.all_tenants().filter(
                id=doc_id, agency_id=prop.agency_id, is_deleted=False
            ).first()
            if not doc:
                raise NotFoundDomainError("سند پیوست‌شده در این آژانس یافت نشد.")
            ver.evidence_document = doc
        else:
            ver.evidence_document = None

    exception_override = bool(data.get("exception_override", False))
    requested_status = data.get("verification_status")

    if exception_override:
        if not can_override:
            raise PermissionDeniedDomainError("فقط مدیر کل یا مدیر مجاز آژانس می‌تواند استثنای احراز اصالت صادر کند.")
        reason = str(data.get("override_reason") or "").strip()
        if len(reason) < 5:
            raise ValidationDomainError("برای صدور استثنای احراز اصالت، ثبت دلیل مستند الزامی است.")
        ver.exception_override = True
        ver.override_reason = reason[:300]
        ver.override_by = user
        ver.verification_status = PropertyVerification.VerificationStatus.EXCEPTION_APPROVED
        ver.verified_by = user
        ver.verified_at = timezone.now()
    elif requested_status:
        if requested_status not in PropertyVerification.VerificationStatus.values:
            raise ValidationDomainError("وضعیت احراز اصالت نامعتبر است.")
        if requested_status in (
            PropertyVerification.VerificationStatus.VERIFIED,
            PropertyVerification.VerificationStatus.REJECTED,
            PropertyVerification.VerificationStatus.EXCEPTION_APPROVED,
        ) and not can_review:
            raise PermissionDeniedDomainError("فقط ناظر یا مدیر مجاز می‌تواند وضعیت نهایی اصالت را تأیید یا رد کند.")
        if requested_status == PropertyVerification.VerificationStatus.EXCEPTION_APPROVED:
            raise ValidationDomainError("برای تایید استثنا باید گزینه استثنا و دلیل آن ارسال شود.")
        if requested_status == PropertyVerification.VerificationStatus.VERIFIED:
            if not (ver.physical_verified and ver.deed_verified and ver.owner_consent_verified):
                raise ValidationDomainError(
                    "برای تأیید نهایی اصالت ملک، هر سه مورد وجود فیزیکی، بررسی سند و رضایت مالک باید تیک بخورند."
                )
            ver.verified_by = user
            ver.verified_at = timezone.now()
            ver.exception_override = False
        ver.verification_status = requested_status
    elif ver.physical_verified and ver.deed_verified and ver.owner_consent_verified and can_review:
        ver.verification_status = PropertyVerification.VerificationStatus.VERIFIED
        ver.verified_by = user
        ver.verified_at = timezone.now()
    elif ver.physical_verified or ver.deed_verified or ver.owner_consent_verified:
        if ver.verification_status == PropertyVerification.VerificationStatus.UNVERIFIED:
            ver.verification_status = PropertyVerification.VerificationStatus.PENDING

    ver.updated_by = user
    ver.save()

    PropertyVerificationHistory.objects.create(
        verification=ver,
        from_status=prev_status,
        to_status=ver.verification_status,
        notes=(ver.override_reason if ver.exception_override else str(data.get("notes") or "")).strip()[:300],
        changed_by=user,
        created_by=user,
    )
    record_audit_event(
        action="PROPERTY_VERIFICATION_EXCEPTION" if ver.exception_override else "PROPERTY_VERIFICATION_UPDATED",
        resource_type="PropertyVerification",
        resource_id=str(ver.id),
        actor=user,
        agency_id=prop.agency_id,
        before_state={"verification_status": prev_status},
        after_state={
            "property_id": str(prop.id),
            "verification_status": ver.verification_status,
            "physical_verified": ver.physical_verified,
            "deed_verified": ver.deed_verified,
            "owner_consent_verified": ver.owner_consent_verified,
            "exception_override": ver.exception_override,
            "override_reason": ver.override_reason,
        },
    )
    return get_property_verification(user=user, agency_id=prop.agency_id, property_id=prop.id)


@transaction.atomic
def submit_violation_report(
    *, user: Optional[User], property_id: UUID, reason_type: str, details: str
) -> PropertyViolationReport:
    prop = Property.objects.all_tenants().filter(id=property_id, is_deleted=False).first()
    if not prop:
        raise NotFoundDomainError("ملک مورد نظر یافت نشد.")
    clean_reason = (reason_type or "OTHER").strip().upper()
    if clean_reason not in PropertyViolationReport.ReasonType.values:
        raise ValidationDomainError("نوع تخلف گزارش‌شده معتبر نیست.")
    clean_details = (details or "").strip()
    if len(clean_details) < 5:
        raise ValidationDomainError("لطفاً توضیحات گزارش تخلف را با جزئیات کافی وارد کنید.")

    report = PropertyViolationReport.objects.create(
        property=prop,
        reporter=user if (user and user.is_authenticated) else None,
        reason_type=clean_reason,
        details=clean_details,
        created_by=user if (user and user.is_authenticated) else None,
    )
    record_audit_event(
        action="PROPERTY_VIOLATION_REPORTED",
        resource_type="PropertyViolationReport",
        resource_id=str(report.id),
        actor=user if (user and user.is_authenticated) else None,
        agency_id=prop.agency_id,
        after_state={"property_id": str(prop.id), "reason_type": clean_reason},
    )
    return report


def list_violation_reports(
    *, user: User, agency_id: Optional[UUID] = None, status_filter: Optional[str] = None
) -> list[PropertyViolationReport]:
    qs = PropertyViolationReport.objects.select_related(
        "property", "property__agency", "reporter", "inspector"
    )
    if is_super_admin(user):
        if agency_id:
            qs = qs.filter(property__agency_id=agency_id)
    elif agency_id and has_agency_permission(user, agency_id, "agency.manage_policy"):
        qs = qs.filter(property__agency_id=agency_id)
    else:
        raise PermissionDeniedDomainError("فقط مدیر کل یا مدیر مجاز آژانس می‌تواند گزارش‌های تخلف را مشاهده کند.")
    if status_filter:
        qs = qs.filter(status=status_filter)
    return list(qs.order_by("-created_at")[:150])


@transaction.atomic
def resolve_violation_report(
    *,
    user: User,
    report_id: UUID,
    resolution_status: str,
    resolution_note: str = "",
    suspend_listing: bool = False,
) -> PropertyViolationReport:
    if not is_super_admin(user):
        raise PermissionDeniedDomainError("فقط تیم مدیریت و نظارت پلتفرم مجاز به بازرسی و صدور حکم گزارش تخلف است.")
    report = PropertyViolationReport.objects.select_related("property").filter(id=report_id).first()
    if not report:
        raise NotFoundDomainError("گزارش تخلف یافت نشد.")
    if resolution_status not in PropertyViolationReport.ReportStatus.values:
        raise ValidationDomainError("وضعیت بررسی گزارش نامعتبر است.")

    prev_status = report.status
    report.status = (
        PropertyViolationReport.ReportStatus.RESOLVED_SUSPENDED
        if suspend_listing
        else resolution_status
    )
    report.inspector = user
    report.resolution_note = (resolution_note or "").strip()
    report.resolved_at = timezone.now()
    report.updated_by = user
    report.save()

    if suspend_listing or report.status == PropertyViolationReport.ReportStatus.RESOLVED_SUSPENDED:
        prop = report.property
        prev_prop_status = prop.status
        prop.status = Property.Status.INACTIVE
        prop.visibility = Property.Visibility.PRIVATE_AGENCY
        prop.updated_by = user
        prop.save(update_fields=["status", "visibility", "updated_by", "updated_at"])
        PropertyStatusHistory.objects.create(
            property=prop,
            from_status=prev_prop_status,
            to_status=Property.Status.INACTIVE,
            reason=f"تعلیق در پی بازرسی تخلف ({report.reason_type}): {report.resolution_note}",
            changed_by=user,
        )

    record_audit_event(
        action="PROPERTY_VIOLATION_RESOLVED",
        resource_type="PropertyViolationReport",
        resource_id=str(report.id),
        actor=user,
        agency_id=report.property.agency_id,
        before_state={"status": prev_status},
        after_state={
            "status": report.status,
            "suspended_listing": bool(suspend_listing or report.status == PropertyViolationReport.ReportStatus.RESOLVED_SUSPENDED),
            "resolution_note": report.resolution_note,
        },
    )
    return report
