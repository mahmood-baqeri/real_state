from decimal import Decimal
from typing import Optional
from uuid import UUID
from django.db import models, transaction
from apps.accounts.models import User
from apps.agencies.models import AgencyAccessPolicy
from apps.audit.services import record_audit_event
from apps.property_media.models import PropertyMedia
from common.exceptions import ConflictDomainError, NotFoundDomainError, PermissionDeniedDomainError
from common.permissions import (
    can_edit_property,
    can_view_owner_pii,
    get_active_membership,
    get_agency_policy,
    has_agency_permission,
    is_super_admin,
)
from common.tenant.context import tenant_bypass
from .models import (
    Amenity,
    DealType,
    Property,
    PropertyAgentAssignment,
    PropertyLocation,
    PropertyOwner,
    PropertyPriceHistory,
    PropertyStatusHistory,
    PropertyType,
)


def get_property_catalog() -> dict:
    return {
        "property_types": list(PropertyType.objects.filter(is_active=True).order_by("name_fa")),
        "deal_types": list(DealType.objects.filter(is_active=True).order_by("name_fa")),
        "amenities": list(Amenity.objects.all().order_by("name_fa")),
    }


def list_public_properties(
    *,
    city: Optional[str] = None,
    district: Optional[str] = None,
    deal_type: Optional[str] = None,
    property_type: Optional[str] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    min_area: Optional[Decimal] = None,
    min_bedrooms: Optional[int] = None,
    q: Optional[str] = None,
    featured_only: bool = False,
):
    with tenant_bypass():
        qs = (
            Property.objects.all_tenants()
            .filter(
                is_deleted=False,
                status=Property.Status.PUBLISHED,
                visibility=Property.Visibility.PUBLIC_PORTAL,
            )
            .select_related("property_type", "deal_type", "location", "agency", "currency")
            .prefetch_related("amenities", "media_items")
        )
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
        if min_bedrooms is not None:
            qs = qs.filter(bedrooms__gte=min_bedrooms)
        if featured_only:
            qs = qs.filter(is_featured=True)
        if q:
            qs = qs.filter(
                models.Q(title__icontains=q)
                | models.Q(property_code__icontains=q)
                | models.Q(location__district__icontains=q)
                | models.Q(location__neighborhood__icontains=q)
            )
        return qs.order_by("-is_featured", "-created_at")


def list_agency_properties(
    *,
    user: User,
    agency_id: Optional[UUID],
    status_filter: Optional[str] = None,
    deal_type: Optional[str] = None,
    property_type: Optional[str] = None,
    q: Optional[str] = None,
):
    if is_super_admin(user) and not agency_id:
        qs = (
            Property.objects.all_tenants()
            .filter(is_deleted=False)
            .select_related("property_type", "deal_type", "location", "agency", "currency", "branch")
            .prefetch_related("amenities", "media_items", "owners__owner_customer", "agent_assignments__membership__user")
        )
    else:
        if not agency_id:
            return Property.objects.none()
        qs = (
            Property.objects.all_tenants()
            .filter(agency_id=agency_id, is_deleted=False)
            .select_related("property_type", "deal_type", "location", "agency", "currency", "branch")
            .prefetch_related("amenities", "media_items", "owners__owner_customer", "agent_assignments__membership__user")
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
    if q:
        qs = qs.filter(
            models.Q(title__icontains=q)
            | models.Q(property_code__icontains=q)
            | models.Q(location__district__icontains=q)
            | models.Q(location__city__icontains=q)
        )
    return qs.order_by("-created_at")


def get_property_for_context(*, user: Optional[User], agency_id: Optional[UUID], property_id: UUID) -> tuple[Property, bool]:
    """Returns (Property, is_internal_agency_view)."""
    if user and user.is_authenticated and (agency_id or is_super_admin(user)):
        prop = list_agency_properties(user=user, agency_id=agency_id).filter(id=property_id).first()
        if prop:
            return prop, True
    prop = list_public_properties().filter(id=property_id).first()
    if not prop:
        raise NotFoundDomainError("ملک مورد نظر یافت نشد.")
    return prop, False


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


@transaction.atomic
def create_property(*, user: User, agency_id: UUID, data: dict) -> Property:
    membership = get_active_membership(user, agency_id)
    if not membership and not is_super_admin(user):
        raise PermissionDeniedDomainError("برای ثبت ملک باید عضو فعال یک آژانس باشید.")

    if Property.objects.all_tenants().filter(agency_id=agency_id, property_code=data["property_code"]).exists():
        raise ConflictDomainError("کد فایل ملک در این آژانس تکراری است.")

    location_data = data.pop("location", None)
    amenity_codes = data.pop("amenity_codes", [])
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

    if amenity_codes:
        prop.amenities.set(Amenity.objects.filter(code__in=amenity_codes))

    if location_data:
        PropertyLocation.objects.create(property=prop, **location_data)

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

    if amenity_codes is not None:
        prop.amenities.set(Amenity.objects.filter(code__in=amenity_codes))

    if location_data is not None:
        PropertyLocation.objects.update_or_create(property=prop, defaults=location_data)

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
    media = PropertyMedia.objects.create(
        property=prop,
        media_type=media_type,
        url=url,
        title=title,
        is_cover=is_cover,
        is_public=is_public,
        created_by=user,
    )
    return media


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
