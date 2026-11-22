from typing import Any, Optional
from uuid import UUID
from django.db import transaction
from apps.accounts.models import User
from apps.audit.services import record_audit_event
from apps.virtual_tours.models import Hotspot, Scene, SceneLink
from apps.virtual_tours.selectors import (
    get_hotspot_for_user,
    get_link_for_user,
    get_scene_for_user,
    get_tour_for_user,
)
from common.exceptions import ValidationDomainError


def list_tour_links(*, user: User, agency_id: Optional[UUID], tour_id: UUID) -> list[SceneLink]:
    tour = get_tour_for_user(user=user, agency_id=agency_id, tour_id=tour_id, require_edit=False)
    return list(tour.links.select_related("source_scene", "target_scene").order_by("created_at"))


@transaction.atomic
def create_scene_link(
    *,
    user: User,
    agency_id: Optional[UUID],
    tour_id: UUID,
    source_scene_id: UUID,
    target_scene_id: UUID,
    yaw: float = 0.0,
    pitch: float = -5.0,
    title: str = "",
    bidirectional: bool = True,
) -> SceneLink:
    tour = get_tour_for_user(user=user, agency_id=agency_id, tour_id=tour_id, require_edit=True)
    if source_scene_id == target_scene_id:
        raise ValidationDomainError("مبدا و مقصد لینک نمی‌توانند یک اتاق یکسان باشند.")

    src = tour.scenes.filter(id=source_scene_id).first()
    dst = tour.scenes.filter(id=target_scene_id).first()
    if not src or not dst:
        raise ValidationDomainError("هر دو اتاق مبدا و مقصد باید متعلق به همین تور مجازی باشند.")

    link = SceneLink.objects.create(
        tour=tour,
        source_scene=src,
        target_scene=dst,
        yaw=float(yaw),
        pitch=float(pitch),
        title=(title or f"ورود به {dst.title}").strip()[:120],
        bidirectional=bool(bidirectional),
        reverse_yaw=(float(yaw) + 180.0) % 360.0 if bidirectional else None,
        created_by=user,
        updated_by=user,
    )
    if bidirectional and not SceneLink.objects.filter(tour=tour, source_scene=dst, target_scene=src).exists():
        SceneLink.objects.create(
            tour=tour,
            source_scene=dst,
            target_scene=src,
            yaw=(float(yaw) + 180.0) % 360.0,
            pitch=float(pitch),
            title=f"بازگشت به {src.title}"[:120],
            bidirectional=True,
            reverse_yaw=float(yaw),
            created_by=user,
            updated_by=user,
        )

    record_audit_event(
        action="virtual_tour.scene_link_create",
        resource_type="SceneLink",
        resource_id=str(link.id),
        actor=user,
        agency_id=tour.agency_id,
        after_state={"source": str(src.id), "target": str(dst.id)},
    )
    return link


@transaction.atomic
def delete_scene_link(*, user: User, agency_id: Optional[UUID], link_id: UUID) -> None:
    link = get_link_for_user(user=user, agency_id=agency_id, link_id=link_id, require_edit=True)
    tour_agency = link.tour.agency_id
    lid = str(link.id)
    link.delete()
    record_audit_event(
        action="virtual_tour.scene_link_delete",
        resource_type="SceneLink",
        resource_id=lid,
        actor=user,
        agency_id=tour_agency,
    )


def list_scene_hotspots(*, user: User, agency_id: Optional[UUID], scene_id: UUID) -> list[Hotspot]:
    scene = get_scene_for_user(user=user, agency_id=agency_id, scene_id=scene_id, require_edit=False)
    return list(scene.hotspots.select_related("target_scene").order_by("created_at"))


@transaction.atomic
def create_hotspot(
    *,
    user: User,
    agency_id: Optional[UUID],
    scene_id: UUID,
    kind: str,
    title: str,
    body: str = "",
    yaw: float = 0.0,
    pitch: float = 0.0,
    target_scene_id: Optional[UUID] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> Hotspot:
    scene = get_scene_for_user(user=user, agency_id=agency_id, scene_id=scene_id, require_edit=True)
    valid_kinds = {k for k, _ in Hotspot.Kind.choices}
    if kind not in valid_kinds:
        raise ValidationDomainError("نوع نقطه تعاملی (Hotspot) معتبر نیست.")

    target_scene = None
    if target_scene_id:
        target_scene = scene.tour.scenes.filter(id=target_scene_id).first()
        if not target_scene:
            raise ValidationDomainError("اتاق مقصد Hotspot باید متعلق به همین تور باشد.")

    hs = Hotspot.objects.create(
        scene=scene,
        kind=kind,
        title=title.strip()[:140],
        body=body.strip(),
        yaw=float(yaw),
        pitch=float(pitch),
        target_scene=target_scene,
        metadata=metadata or {},
        created_by=user,
        updated_by=user,
    )
    return hs


@transaction.atomic
def update_hotspot(
    *,
    user: User,
    agency_id: Optional[UUID],
    hotspot_id: UUID,
    data: dict[str, Any],
) -> Hotspot:
    hs = get_hotspot_for_user(user=user, agency_id=agency_id, hotspot_id=hotspot_id, require_edit=True)
    if data.get("kind") is not None:
        valid_kinds = {k for k, _ in Hotspot.Kind.choices}
        if data["kind"] not in valid_kinds:
            raise ValidationDomainError("نوع Hotspot معتبر نیست.")
        hs.kind = data["kind"]
    if data.get("title") is not None:
        hs.title = str(data["title"]).strip()[:140]
    if data.get("body") is not None:
        hs.body = str(data["body"]).strip()
    if data.get("yaw") is not None:
        hs.yaw = float(data["yaw"])
    if data.get("pitch") is not None:
        hs.pitch = float(data["pitch"])
    if "target_scene_id" in data:
        ts_id = data["target_scene_id"]
        if ts_id is None:
            hs.target_scene = None
        else:
            ts = hs.scene.tour.scenes.filter(id=ts_id).first()
            if not ts:
                raise ValidationDomainError("اتاق مقصد نامعتبر است.")
            hs.target_scene = ts
    if isinstance(data.get("metadata"), dict):
        hs.metadata = data["metadata"]
    hs.updated_by = user
    hs.save()
    return hs


@transaction.atomic
def delete_hotspot(*, user: User, agency_id: Optional[UUID], hotspot_id: UUID) -> None:
    hs = get_hotspot_for_user(user=user, agency_id=agency_id, hotspot_id=hotspot_id, require_edit=True)
    hs.delete()
