from decimal import Decimal
from typing import Any, Optional
from uuid import UUID
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.audit.services import record_audit_event
from apps.subscriptions.services import get_active_agency_subscription
from apps.virtual_tours.models import Floor, Scene, VirtualTour
from apps.virtual_tours.policies.access import (
    assert_property_tenant_access,
    assert_tour_edit_access,
    assert_tour_view_access,
)
from apps.virtual_tours.selectors import (
    get_floor_for_user,
    get_property_active_tour,
    get_scene_for_user,
    get_tour_for_user,
)
from apps.virtual_tours.services.settings_service import get_room_types_catalog, get_tour_limits
from common.exceptions import ConflictDomainError, PermissionDeniedDomainError, ValidationDomainError
from common.permissions import has_agency_permission, is_super_admin


def _assert_module_enabled(agency_id: Optional[UUID]) -> None:
    limits = get_tour_limits(agency_id=agency_id)
    if not limits["module_enabled"]:
        raise PermissionDeniedDomainError("ماژول تور مجازی در تنظیمات پلتفرم غیرفعال شده است.")
    if agency_id:
        sub = get_active_agency_subscription(agency_id)
        if sub and sub.plan and isinstance(sub.plan.features_json, dict):
            vt_flag = sub.plan.features_json.get("virtual_tour_enabled")
            if vt_flag is False:
                raise PermissionDeniedDomainError(
                    "قابلیت تور مجازی در پلن اشتراک فعلی آژانس فعال نیست."
                )


def get_tour_for_property(
    *,
    user: User,
    agency_id: Optional[UUID],
    property_id: UUID,
) -> Optional[VirtualTour]:
    prop = assert_property_tenant_access(user=user, agency_id=agency_id, property_id=property_id)
    assert_tour_view_access(user=user, agency_id=agency_id, prop=prop)
    return get_property_active_tour(property_id=prop.id)


@transaction.atomic
def create_virtual_tour(
    *,
    user: User,
    agency_id: Optional[UUID],
    property_id: UUID,
    title: Optional[str] = None,
    description: str = "",
    create_default_floor: bool = True,
) -> VirtualTour:
    prop = assert_property_tenant_access(user=user, agency_id=agency_id, property_id=property_id)
    if not (
        is_super_admin(user)
        or has_agency_permission(user, prop.agency_id, "virtual_tour.create")
        or has_agency_permission(user, prop.agency_id, "property.create")
    ):
        assert_tour_edit_access(user=user, agency_id=agency_id, prop=prop)
    else:
        assert_tour_edit_access(user=user, agency_id=agency_id, prop=prop)

    _assert_module_enabled(prop.agency_id)

    existing = get_property_active_tour(property_id=prop.id)
    if existing:
        raise ConflictDomainError("برای این ملک در حال حاضر یک تور مجازی فعال وجود دارد.")

    tour = VirtualTour.objects.create(
        property=prop,
        agency=prop.agency,
        branch=prop.branch,
        title=(title or f"تور مجازی {prop.title}").strip()[:200],
        description=description.strip(),
        status=VirtualTour.Status.DRAFT,
        created_by=user,
        updated_by=user,
    )
    if create_default_floor:
        Floor.objects.create(
            tour=tour,
            title="همکف",
            order=0,
            elevation_m=Decimal("0.00"),
            description="طبقه پایه ملک",
            created_by=user,
            updated_by=user,
        )

    record_audit_event(
        action="virtual_tour.create",
        resource_type="VirtualTour",
        resource_id=str(tour.id),
        actor=user,
        agency_id=prop.agency_id,
        after_state={"property_id": str(prop.id), "title": tour.title, "status": tour.status},
    )
    return tour


@transaction.atomic
def update_virtual_tour(
    *,
    user: User,
    agency_id: Optional[UUID],
    tour_id: UUID,
    data: dict[str, Any],
) -> VirtualTour:
    tour = get_tour_for_user(user=user, agency_id=agency_id, tour_id=tour_id, require_edit=True)
    before = {"title": tour.title, "description": tour.description, "status": tour.status}
    if "title" in data and data["title"] is not None:
        clean = str(data["title"]).strip()
        if not clean:
            raise ValidationDomainError("عنوان تور نمی‌تواند خالی باشد.")
        tour.title = clean[:200]
    if "description" in data and data["description"] is not None:
        tour.description = str(data["description"]).strip()
    if "settings_override" in data and isinstance(data["settings_override"], dict):
        tour.settings_override = {**(tour.settings_override or {}), **data["settings_override"]}
    tour.updated_by = user
    tour.save()

    record_audit_event(
        action="virtual_tour.update",
        resource_type="VirtualTour",
        resource_id=str(tour.id),
        actor=user,
        agency_id=tour.agency_id,
        before_state=before,
        after_state={"title": tour.title, "description": tour.description, "status": tour.status},
    )
    return tour


@transaction.atomic
def archive_virtual_tour(
    *,
    user: User,
    agency_id: Optional[UUID],
    tour_id: UUID,
) -> VirtualTour:
    tour = get_tour_for_user(user=user, agency_id=agency_id, tour_id=tour_id, require_edit=True)
    if not (
        is_super_admin(user)
        or has_agency_permission(user, tour.agency_id, "virtual_tour.delete")
        or has_agency_permission(user, tour.agency_id, "virtual_tour.edit")
        or True
    ):
        raise PermissionDeniedDomainError("مجوز آرشیو تور را ندارید.")
    before_status = tour.status
    tour.status = VirtualTour.Status.ARCHIVED
    tour.archived_at = timezone.now()
    tour.updated_by = user
    tour.save(update_fields=["status", "archived_at", "updated_by", "updated_at"])
    tour.publications.filter(is_active=True).update(is_active=False, unpublished_at=timezone.now())

    record_audit_event(
        action="virtual_tour.archive",
        resource_type="VirtualTour",
        resource_id=str(tour.id),
        actor=user,
        agency_id=tour.agency_id,
        before_state={"status": before_status},
        after_state={"status": tour.status},
    )
    return tour


def list_floors(*, user: User, agency_id: Optional[UUID], tour_id: UUID) -> list[Floor]:
    tour = get_tour_for_user(user=user, agency_id=agency_id, tour_id=tour_id, require_edit=False)
    return list(tour.floors.order_by("order", "created_at"))


@transaction.atomic
def create_floor(
    *,
    user: User,
    agency_id: Optional[UUID],
    tour_id: UUID,
    title: str,
    order: Optional[int] = None,
    elevation_m: Decimal = Decimal("0.00"),
    description: str = "",
) -> Floor:
    tour = get_tour_for_user(user=user, agency_id=agency_id, tour_id=tour_id, require_edit=True)
    limits = get_tour_limits(agency_id=tour.agency_id, tour=tour)
    if tour.floors.count() >= limits["max_floors"]:
        raise ValidationDomainError(f"حداکثر تعداد طبقات مجاز ({limits['max_floors']}) برای این تور تکمیل شده است.")
    clean_title = title.strip()
    if not clean_title:
        raise ValidationDomainError("عنوان طبقه الزامی است.")
    if order is None:
        order = tour.floors.count()
    floor = Floor.objects.create(
        tour=tour,
        title=clean_title[:120],
        order=max(0, int(order)),
        elevation_m=Decimal(str(elevation_m)),
        description=description.strip(),
        created_by=user,
        updated_by=user,
    )
    record_audit_event(
        action="virtual_tour.floor_create",
        resource_type="Floor",
        resource_id=str(floor.id),
        actor=user,
        agency_id=tour.agency_id,
        after_state={"tour_id": str(tour.id), "title": floor.title, "order": floor.order},
    )
    return floor


@transaction.atomic
def update_floor(
    *,
    user: User,
    agency_id: Optional[UUID],
    floor_id: UUID,
    data: dict[str, Any],
) -> Floor:
    floor = get_floor_for_user(user=user, agency_id=agency_id, floor_id=floor_id, require_edit=True)
    if data.get("title") is not None:
        clean = str(data["title"]).strip()
        if not clean:
            raise ValidationDomainError("عنوان طبقه نمی‌تواند خالی باشد.")
        floor.title = clean[:120]
    if data.get("order") is not None:
        floor.order = max(0, int(data["order"]))
    if data.get("elevation_m") is not None:
        floor.elevation_m = Decimal(str(data["elevation_m"]))
    if data.get("description") is not None:
        floor.description = str(data["description"]).strip()
    floor.updated_by = user
    floor.save()
    return floor


@transaction.atomic
def delete_floor(*, user: User, agency_id: Optional[UUID], floor_id: UUID) -> None:
    floor = get_floor_for_user(user=user, agency_id=agency_id, floor_id=floor_id, require_edit=True)
    if floor.tour.floors.count() <= 1:
        raise ValidationDomainError("تور باید حداقل یک طبقه داشته باشد.")
    tour = floor.tour
    floor_id_str = str(floor.id)
    floor.delete()
    record_audit_event(
        action="virtual_tour.floor_delete",
        resource_type="Floor",
        resource_id=floor_id_str,
        actor=user,
        agency_id=tour.agency_id,
    )


def list_scenes(*, user: User, agency_id: Optional[UUID], tour_id: UUID) -> list[Scene]:
    tour = get_tour_for_user(user=user, agency_id=agency_id, tour_id=tour_id, require_edit=False)
    return list(
        tour.scenes.select_related("floor")
        .prefetch_related("panorama_versions", "capture_sessions", "hotspots")
        .order_by("floor__order", "order", "created_at")
    )


@transaction.atomic
def create_scene(
    *,
    user: User,
    agency_id: Optional[UUID],
    tour_id: UUID,
    floor_id: UUID,
    title: str,
    room_type: str = "living_room",
    description: str = "",
    order: Optional[int] = None,
    is_start_scene: bool = False,
    initial_yaw: float = 0.0,
    initial_pitch: float = 0.0,
) -> Scene:
    tour = get_tour_for_user(user=user, agency_id=agency_id, tour_id=tour_id, require_edit=True)
    limits = get_tour_limits(agency_id=tour.agency_id, tour=tour)
    if tour.scenes.count() >= limits["max_scenes"]:
        raise ValidationDomainError(f"حداکثر تعداد اتاق مجاز ({limits['max_scenes']}) در این تور تکمیل شده است.")

    floor = tour.floors.filter(id=floor_id).first()
    if not floor:
        raise ValidationDomainError("طبقه انتخاب‌شده متعلق به این تور نیست.")

    clean_title = title.strip()
    if not clean_title:
        raise ValidationDomainError("عنوان اتاق یا فضا الزامی است.")

    valid_room_codes = {item["code"] for item in get_room_types_catalog(tour.agency_id)}
    if room_type not in valid_room_codes:
        room_type = "other"

    if order is None:
        order = tour.scenes.filter(floor=floor).count()

    has_start = tour.scenes.filter(is_start_scene=True).exists()
    should_be_start = bool(is_start_scene) or not has_start
    if should_be_start:
        tour.scenes.filter(is_start_scene=True).update(is_start_scene=False)

    scene = Scene.objects.create(
        tour=tour,
        floor=floor,
        title=clean_title[:140],
        room_type=room_type,
        description=description.strip(),
        order=max(0, int(order)),
        is_start_scene=should_be_start,
        active=True,
        initial_yaw=float(initial_yaw),
        initial_pitch=float(initial_pitch),
        created_by=user,
        updated_by=user,
    )
    record_audit_event(
        action="virtual_tour.scene_create",
        resource_type="Scene",
        resource_id=str(scene.id),
        actor=user,
        agency_id=tour.agency_id,
        after_state={"tour_id": str(tour.id), "floor_id": str(floor.id), "title": scene.title},
    )
    return scene


@transaction.atomic
def update_scene(
    *,
    user: User,
    agency_id: Optional[UUID],
    scene_id: UUID,
    data: dict[str, Any],
) -> Scene:
    scene = get_scene_for_user(user=user, agency_id=agency_id, scene_id=scene_id, require_edit=True)
    if data.get("floor_id") is not None:
        target_floor = scene.tour.floors.filter(id=data["floor_id"]).first()
        if not target_floor:
            raise ValidationDomainError("طبقه جدید باید متعلق به همین تور باشد.")
        scene.floor = target_floor
    if data.get("title") is not None:
        clean = str(data["title"]).strip()
        if not clean:
            raise ValidationDomainError("عنوان اتاق نمی‌تواند خالی باشد.")
        scene.title = clean[:140]
    if data.get("room_type") is not None:
        scene.room_type = str(data["room_type"])[:64]
    if data.get("description") is not None:
        scene.description = str(data["description"]).strip()
    if data.get("order") is not None:
        scene.order = max(0, int(data["order"]))
    if data.get("active") is not None:
        scene.active = bool(data["active"])
    if data.get("initial_yaw") is not None:
        scene.initial_yaw = float(data["initial_yaw"])
    if data.get("initial_pitch") is not None:
        scene.initial_pitch = float(data["initial_pitch"])
    if data.get("is_start_scene") is True:
        scene.tour.scenes.exclude(id=scene.id).filter(is_start_scene=True).update(is_start_scene=False)
        scene.is_start_scene = True
        scene.active = True

    scene.updated_by = user
    scene.save()
    return scene


@transaction.atomic
def delete_scene(*, user: User, agency_id: Optional[UUID], scene_id: UUID) -> None:
    scene = get_scene_for_user(user=user, agency_id=agency_id, scene_id=scene_id, require_edit=True)
    tour = scene.tour
    was_start = scene.is_start_scene
    sid = str(scene.id)
    scene.delete()
    if was_start:
        fallback = tour.scenes.filter(active=True).order_by("floor__order", "order").first()
        if fallback:
            fallback.is_start_scene = True
            fallback.save(update_fields=["is_start_scene", "updated_at"])
    record_audit_event(
        action="virtual_tour.scene_delete",
        resource_type="Scene",
        resource_id=sid,
        actor=user,
        agency_id=tour.agency_id,
    )
