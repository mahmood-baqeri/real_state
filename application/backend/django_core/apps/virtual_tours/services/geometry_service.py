import math
from decimal import Decimal
from io import BytesIO
from typing import Any, Optional
from uuid import UUID

import cv2
import numpy as np
import trimesh
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.accounts.models import User
from apps.audit.services import record_audit_event
from apps.virtual_tours.models import (
    BuildingGeometry,
    Floor,
    FloorPlanAsset,
    GeneratedModelAsset,
    ModelReview,
    ProcessingJob,
    RoomGeometry,
    RoomMeasurement,
    Scene,
    VirtualTour,
    WallOpening,
    WallSegment,
)
from apps.virtual_tours.policies.access import assert_tour_approve_access
from apps.virtual_tours.selectors import get_floor_for_user, get_scene_for_user, get_tour_for_user
from apps.virtual_tours.services.settings_service import get_vt_setting
from common.exceptions import ConflictDomainError, NotFoundDomainError, ValidationDomainError
from integrations.registry import get_storage_provider
from integrations.storage import validate_uploaded_file

ALLOWED_FLOORPLAN_MIMES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}

ROOM_COLORS = {
    "living_room": "#0F766E",
    "sitting_room": "#0D9488",
    "kitchen": "#D97706",
    "dining_room": "#B45309",
    "bedroom": "#4F46E5",
    "bathroom": "#0284C7",
    "restroom": "#0369A1",
    "hallway": "#64748B",
    "balcony": "#059669",
    "terrace": "#10B981",
    "office": "#7C3AED",
    "other": "#475569",
}


def _hex_to_rgba(hex_str: str, alpha: int = 255) -> list[int]:
    cleaned = (hex_str or "#0F766E").strip().lstrip("#")
    if len(cleaned) != 6:
        return [15, 118, 110, alpha]
    try:
        return [int(cleaned[0:2], 16), int(cleaned[2:4], 16), int(cleaned[4:6], 16), alpha]
    except ValueError:
        return [15, 118, 110, alpha]


def _render_pdf_blueprint_preview(pdf_bytes: bytes, filename: str) -> tuple[int, int, bytes]:
    """
    Rasterize the first page of a real architectural PDF to PNG.
    Rendering is deliberately bounded to avoid excessive memory use from hostile PDFs.
    """
    try:
        import fitz  # type: ignore # PyMuPDF
    except ImportError as exc:
        raise ValidationDomainError(
            "برای پیش‌نمایش PDF، وابستگی PyMuPDF نصب نشده است."
        ) from exc

    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
        if document.is_encrypted or document.page_count < 1:
            raise ValidationDomainError("فایل PDF رمزگذاری‌شده یا فاقد صفحه معتبر است.")
        page = document.load_page(0)
        rect = page.rect
        if rect.width <= 0 or rect.height <= 0:
            raise ValidationDomainError("ابعاد صفحه اول PDF معتبر نیست.")

        # Keep the longest rendered edge at or below 2400px.
        scale = min(2.5, 2400.0 / max(rect.width, rect.height))
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False, colorspace=fitz.csRGB)
        if pix.width < 100 or pix.height < 100 or pix.width * pix.height > 6_000_000:
            raise ValidationDomainError("ابعاد پیش‌نمایش PDF خارج از محدوده مجاز است.")
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        output = BytesIO()
        image.save(output, format="PNG", optimize=True)
        document.close()
        return pix.width, pix.height, output.getvalue()
    except ValidationDomainError:
        raise
    except Exception as exc:
        raise ValidationDomainError("امکان خواندن یا تبدیل صفحه اول PDF وجود ندارد.") from exc


def compute_polygon_metrics(points: list[list[float]]) -> dict[str, Any]:
    if not isinstance(points, list) or len(points) < 3:
        raise ValidationDomainError("پلیگون اتاق باید حداقل دارای ۳ نقطه (رأس) باشد.")
    pts: list[tuple[float, float]] = []
    for pt in points:
        if not isinstance(pt, (list, tuple)) or len(pt) < 2:
            raise ValidationDomainError("فرمت نقاط پلیگون نامعتبر است؛ هر نقطه باید [x, y] باشد.")
        try:
            x, y = float(pt[0]), float(pt[1])
        except (TypeError, ValueError) as exc:
            raise ValidationDomainError("مختصات پلیگون باید عددی باشد.") from exc
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValidationDomainError("مختصات پلیگون نامعتبر است.")
        pts.append((round(x, 4), round(y, 4)))

    n = len(pts)
    area2 = 0.0
    perim = 0.0
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        area2 += x1 * y2 - x2 * y1
        perim += math.hypot(x2 - x1, y2 - y1)
    area = abs(area2) * 0.5
    if area < 0.1:
        raise ValidationDomainError("مساحت اتاق بسیار کوچک یا خطی است (حداقل ۰٫۱ مترمربع).")

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return {
        "points": [[p[0], p[1]] for p in pts],
        "area_sqm": Decimal(f"{area:.2f}"),
        "perimeter_m": Decimal(f"{perim:.2f}"),
        "width_m": Decimal(f"{max(xs) - min(xs):.2f}"),
        "length_m": Decimal(f"{max(ys) - min(ys):.2f}"),
        "bounds": {"min_x": min(xs), "min_y": min(ys), "max_x": max(xs), "max_y": max(ys)},
    }


def _sync_building_geometry(tour: VirtualTour) -> BuildingGeometry:
    rooms = list(tour.room_geometries.all())
    total_area = sum((r.area_sqm for r in rooms), Decimal("0.00"))
    all_pts = [pt for r in rooms for pt in (r.polygon_points or [])]
    bounds = {}
    if all_pts:
        xs = [float(p[0]) for p in all_pts]
        ys = [float(p[1]) for p in all_pts]
        bounds = {"min_x": min(xs), "min_y": min(ys), "max_x": max(xs), "max_y": max(ys)}

    default_h = float(get_vt_setting("virtual_tour.dollhouse_wall_height_m", 2.90, tour=tour) or 2.90)
    default_t = float(get_vt_setting("virtual_tour.dollhouse_wall_thickness_m", 0.18, tour=tour) or 0.18)

    bg, _ = BuildingGeometry.objects.update_or_create(
        tour=tour,
        defaults={
            "default_wall_height_m": default_h,
            "default_wall_thickness_m": default_t,
            "slab_thickness_m": 0.22,
            "footprint_bounds": bounds,
            "total_area_sqm": total_area,
            "geometry_source": "floorplan_2d_extrusion",
        },
    )
    return bg


@transaction.atomic
def upload_floorplan(
    *,
    user: User,
    agency_id: Optional[UUID],
    tour_id: UUID,
    floor_id: UUID,
    filename: str,
    content_type: str,
    content: bytes,
) -> FloorPlanAsset:
    tour = get_tour_for_user(user=user, agency_id=agency_id, tour_id=tour_id, require_edit=True)
    floor = get_floor_for_user(user=user, agency_id=agency_id, floor_id=floor_id, require_edit=True)
    if floor.tour_id != tour.id:
        raise ValidationDomainError("طبقه انتخاب‌شده متعلق به این تور نیست.")

    safe_name, mime = validate_uploaded_file(
        filename=filename,
        content_type=content_type,
        content=content,
        max_bytes=25 * 1024 * 1024,
    )
    if mime not in ALLOWED_FLOORPLAN_MIMES:
        raise ValidationDomainError("برای فایل پلان فقط فرمت‌های PNG، JPG، WebP و PDF مجاز است.")

    storage = get_storage_provider()
    prefix = f"private/virtual_tours/{tour.agency_id}/{tour.id}/floorplans/{floor.id}"

    if mime == "application/pdf":
        if not content[:8].startswith(b"%PDF-"):
            raise ValidationDomainError("ساختار فایل PDF پلان معتبر نیست.")
        width, height, preview_bytes = _render_pdf_blueprint_preview(content, safe_name)
        stored = storage.put_bytes(
            key_prefix=prefix,
            safe_filename=safe_name,
            content=content,
            mime_type=mime,
        )
        preview_stored = storage.put_bytes(
            key_prefix=prefix,
            safe_filename=f"preview-{safe_name}.png",
            content=preview_bytes,
            mime_type="image/png",
        )
        file_type = "pdf"
        preview_key = preview_stored.file_key
    else:
        try:
            with Image.open(BytesIO(content)) as im:
                im.verify()
            with Image.open(BytesIO(content)) as im2:
                oriented = ImageOps.exif_transpose(im2)
                width, height = oriented.size
                if width < 100 or height < 100:
                    raise ValidationDomainError("ابعاد تصویر پلان بسیار کوچک است.")
                if oriented.mode not in ("RGB", "RGBA"):
                    oriented = oriented.convert("RGB")
                buf = BytesIO()
                fmt = "JPEG" if mime == "image/jpeg" else ("WEBP" if mime == "image/webp" else "PNG")
                if fmt == "JPEG" and oriented.mode == "RGBA":
                    oriented = oriented.convert("RGB")
                oriented.save(buf, format=fmt, quality=92)
                norm_bytes = buf.getvalue()
        except ValidationDomainError:
            raise
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ValidationDomainError("فایل تصویر پلان آسیب‌دیده یا نامعتبر است.") from exc

        stored = storage.put_bytes(
            key_prefix=prefix,
            safe_filename=safe_name,
            content=norm_bytes,
            mime_type=mime,
        )
        file_type = mime.split("/")[-1]
        preview_key = stored.file_key

    tour.floorplans.filter(floor=floor, is_active=True).update(is_active=False)
    fp = FloorPlanAsset.objects.create(
        tour=tour,
        floor=floor,
        file_type=file_type,
        storage_key=stored.file_key,
        preview_storage_key=preview_key,
        filename=safe_name,
        mime_type=mime,
        size_bytes=stored.size_bytes,
        width_px=int(width),
        height_px=int(height),
        is_active=True,
        created_by=user,
        updated_by=user,
    )
    record_audit_event(
        action="virtual_tour.floorplan_upload",
        resource_type="FloorPlanAsset",
        resource_id=str(fp.id),
        actor=user,
        agency_id=tour.agency_id,
        after_state={"floor_id": str(floor.id), "filename": safe_name, "file_type": file_type},
    )
    return fp


@transaction.atomic
def calibrate_floorplan(
    *,
    user: User,
    agency_id: Optional[UUID],
    floorplan_id: UUID,
    point_a: list[float],
    point_b: list[float],
    real_distance_m: float,
) -> FloorPlanAsset:
    fp = FloorPlanAsset.objects.select_related("tour", "tour__property", "floor").filter(id=floorplan_id).first()
    if not fp:
        raise NotFoundDomainError("پلان مورد نظر یافت نشد.")
    get_tour_for_user(user=user, agency_id=agency_id, tour_id=fp.tour_id, require_edit=True)

    if real_distance_m <= 0.05 or real_distance_m > 500:
        raise ValidationDomainError("طول واقعی انتخاب‌شده برای کالیبراسیون باید بین ۰٫۰۵ تا ۵۰۰ متر باشد.")
    if len(point_a) < 2 or len(point_b) < 2:
        raise ValidationDomainError("مختصات دو نقطه مرجع کالیبراسیون الزامی است.")

    try:
        ax, ay = float(point_a[0]), float(point_a[1])
        bx, by = float(point_b[0]), float(point_b[1])
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValidationDomainError("مختصات کالیبراسیون باید عددی باشند.") from exc
    if not all(math.isfinite(v) for v in (ax, ay, bx, by)):
        raise ValidationDomainError("مختصات کالیبراسیون معتبر نیست.")
    if not (0 <= ax < fp.width_px and 0 <= bx < fp.width_px and 0 <= ay < fp.height_px and 0 <= by < fp.height_px):
        raise ValidationDomainError("نقاط کالیبراسیون باید داخل محدوده تصویر پلان باشند.")

    px_dist = math.hypot(bx - ax, by - ay)
    if px_dist < 5.0:
        raise ValidationDomainError("فاصله دو نقطه روی تصویر پلان برای کالیبراسیون دقیق بسیار کم است (حداقل ۵ پیکسل).")

    scale = round(float(real_distance_m) / px_dist, 6)
    fp.scale_m_per_px = scale
    fp.calibration_data = {
        "point_a": [round(ax, 2), round(ay, 2)],
        "point_b": [round(bx, 2), round(by, 2)],
        "pixel_distance": round(px_dist, 2),
        "real_distance_m": round(float(real_distance_m), 3),
        "scale_m_per_px": scale,
        "calibrated_at": timezone.now().isoformat(),
    }
    fp.updated_by = user
    fp.save(update_fields=["scale_m_per_px", "calibration_data", "updated_by", "updated_at"])

    record_audit_event(
        action="virtual_tour.floorplan_calibrate",
        resource_type="FloorPlanAsset",
        resource_id=str(fp.id),
        actor=user,
        agency_id=fp.tour.agency_id,
        after_state={"scale_m_per_px": scale, "real_distance_m": real_distance_m},
    )
    return fp


@transaction.atomic
def create_or_update_room_geometry(
    *,
    user: User,
    agency_id: Optional[UUID],
    tour_id: UUID,
    data: dict[str, Any],
    room_id: Optional[UUID] = None,
) -> RoomGeometry:
    tour = get_tour_for_user(user=user, agency_id=agency_id, tour_id=tour_id, require_edit=True)
    floor = get_floor_for_user(user=user, agency_id=agency_id, floor_id=data["floor_id"], require_edit=True)
    if floor.tour_id != tour.id:
        raise ValidationDomainError("طبقه انتخاب‌شده متعلق به این تور نیست.")

    scene = None
    if data.get("scene_id"):
        scene = get_scene_for_user(user=user, agency_id=agency_id, scene_id=data["scene_id"], require_edit=True)
        if scene.tour_id != tour.id:
            raise ValidationDomainError("صحنه انتخاب‌شده متعلق به این تور نیست.")

    if not data.get("floorplan_id"):
        raise ValidationDomainError("برای ترسیم اتاق، انتخاب پلان همان طبقه الزامی است.")

    floorplan = tour.floorplans.filter(
        id=data["floorplan_id"], floor=floor, is_active=True
    ).first()
    if not floorplan:
        raise ValidationDomainError("پلان انتخاب‌شده فعال نیست یا متعلق به همین طبقه و تور نیست.")
    if not floorplan.scale_m_per_px or floorplan.scale_m_per_px <= 0:
        raise ValidationDomainError("ابتدا مقیاس پلان را کالیبره کنید.")

    metrics = compute_polygon_metrics(data["polygon_points"])
    room_type = (data.get("room_type") or (scene.room_type if scene else "living_room")).strip()
    label = (data.get("label") or (scene.title if scene else "اتاق")).strip()
    height_m = Decimal(str(data.get("height_m") or get_vt_setting("virtual_tour.dollhouse_wall_height_m", 2.90, tour=tour) or 2.90))
    if height_m < Decimal("1.8") or height_m > Decimal("12.0"):
        raise ValidationDomainError("ارتفاع سقف اتاق باید بین ۱٫۸ تا ۱۲ متر باشد.")
    color_hex = data.get("color_hex") or ROOM_COLORS.get(room_type, "#0F766E")

    if room_id:
        room = tour.room_geometries.filter(id=room_id).first()
        if not room:
            raise NotFoundDomainError("هندسه اتاق مورد نظر یافت نشد.")
        room.floor = floor
        room.scene = scene
        room.floorplan = floorplan or room.floorplan
        room.label = label
        room.room_type = room_type
        room.polygon_points = metrics["points"]
        room.area_sqm = metrics["area_sqm"]
        room.perimeter_m = metrics["perimeter_m"]
        room.height_m = height_m
        room.color_hex = color_hex
        room.updated_by = user
        room.save()
    else:
        room = RoomGeometry.objects.create(
            tour=tour,
            floor=floor,
            scene=scene,
            floorplan=floorplan,
            label=label,
            room_type=room_type,
            polygon_points=metrics["points"],
            area_sqm=metrics["area_sqm"],
            perimeter_m=metrics["perimeter_m"],
            height_m=height_m,
            source="floorplan_2d",
            color_hex=color_hex,
            created_by=user,
            updated_by=user,
        )

    if scene:
        scene.width_m = metrics["width_m"]
        scene.length_m = metrics["length_m"]
        scene.height_m = height_m
        scene.polygon_json = metrics["points"]
        scene.geometry_source = "floorplan_2d"
        scene.updated_by = user
        scene.save(update_fields=["width_m", "length_m", "height_m", "polygon_json", "geometry_source", "updated_by", "updated_at"])

    _sync_building_geometry(tour)
    return room


@transaction.atomic
def delete_room_geometry(*, user: User, agency_id: Optional[UUID], room_id: UUID) -> dict[str, Any]:
    room = RoomGeometry.objects.select_related("tour", "tour__property", "scene").filter(id=room_id).first()
    if not room:
        raise NotFoundDomainError("هندسه اتاق مورد نظر یافت نشد.")
    tour = get_tour_for_user(user=user, agency_id=agency_id, tour_id=room.tour_id, require_edit=True)
    rid = str(room.id)
    room.delete()
    _sync_building_geometry(tour)
    return {"deleted": True, "id": rid}


@transaction.atomic
def create_wall_segment(
    *,
    user: User,
    agency_id: Optional[UUID],
    tour_id: UUID,
    data: dict[str, Any],
) -> WallSegment:
    tour = get_tour_for_user(user=user, agency_id=agency_id, tour_id=tour_id, require_edit=True)
    floor = get_floor_for_user(user=user, agency_id=agency_id, floor_id=data["floor_id"], require_edit=True)
    if floor.tour_id != tour.id:
        raise ValidationDomainError("طبقه انتخاب‌شده متعلق به این تور نیست.")

    sx, sy = float(data["start_x"]), float(data["start_y"])
    ex, ey = float(data["end_x"]), float(data["end_y"])
    if math.hypot(ex - sx, ey - sy) < 0.15:
        raise ValidationDomainError("طول دیوار باید حداقل ۰٫۱۵ متر باشد.")

    thickness = float(data.get("thickness_m") or get_vt_setting("virtual_tour.dollhouse_wall_thickness_m", 0.18, tour=tour) or 0.18)
    height = float(data.get("height_m") or get_vt_setting("virtual_tour.dollhouse_wall_height_m", 2.90, tour=tour) or 2.90)

    if not data.get("floorplan_id"):
        raise ValidationDomainError("برای ترسیم دیوار، انتخاب پلان همان طبقه الزامی است.")
    floorplan = tour.floorplans.filter(
        id=data["floorplan_id"], floor=floor, is_active=True
    ).first()
    if not floorplan:
        raise ValidationDomainError("پلان انتخاب‌شده فعال نیست یا متعلق به همین طبقه و تور نیست.")
    if not floorplan.scale_m_per_px or floorplan.scale_m_per_px <= 0:
        raise ValidationDomainError("ابتدا مقیاس پلان را کالیبره کنید.")

    wall = WallSegment.objects.create(
        tour=tour,
        floor=floor,
        floorplan=floorplan,
        start_x=round(sx, 4),
        start_y=round(sy, 4),
        end_x=round(ex, 4),
        end_y=round(ey, 4),
        thickness_m=max(0.05, min(1.0, thickness)),
        height_m=max(1.5, min(12.0, height)),
        is_exterior=bool(data.get("is_exterior", False)),
        created_by=user,
        updated_by=user,
    )
    return wall


@transaction.atomic
def delete_wall_segment(*, user: User, agency_id: Optional[UUID], wall_id: UUID) -> dict[str, Any]:
    wall = WallSegment.objects.select_related("tour", "tour__property").filter(id=wall_id).first()
    if not wall:
        raise NotFoundDomainError("دیوار مورد نظر یافت نشد.")
    get_tour_for_user(user=user, agency_id=agency_id, tour_id=wall.tour_id, require_edit=True)
    wid = str(wall.id)
    wall.delete()
    return {"deleted": True, "id": wid}


@transaction.atomic
def create_wall_opening(
    *,
    user: User,
    agency_id: Optional[UUID],
    wall_id: UUID,
    data: dict[str, Any],
) -> WallOpening:
    wall = WallSegment.objects.select_related("tour", "tour__property").filter(id=wall_id).first()
    if not wall:
        raise NotFoundDomainError("دیوار مورد نظر یافت نشد.")
    get_tour_for_user(user=user, agency_id=agency_id, tour_id=wall.tour_id, require_edit=True)

    wall_len = math.hypot(wall.end_x - wall.start_x, wall.end_y - wall.start_y)
    width_m = float(data.get("width_m") or 0.95)
    if width_m <= 0.2 or width_m >= wall_len:
        raise ValidationDomainError("عرض بازشو باید کمتر از طول دیوار و بزرگ‌تر از ۰٫۲ متر باشد.")

    opening = WallOpening.objects.create(
        wall=wall,
        kind=data.get("kind") or WallOpening.Kind.DOOR,
        offset_ratio=max(0.08, min(0.92, float(data.get("offset_ratio", 0.5)))),
        width_m=width_m,
        height_m=min(wall.height_m - 0.1, max(0.4, float(data.get("height_m", 2.10)))),
        sill_height_m=max(0.0, min(2.0, float(data.get("sill_height_m", 0.0)))),
        created_by=user,
        updated_by=user,
    )
    return opening


@transaction.atomic
def delete_wall_opening(*, user: User, agency_id: Optional[UUID], opening_id: UUID) -> dict[str, Any]:
    op = WallOpening.objects.select_related("wall", "wall__tour", "wall__tour__property").filter(id=opening_id).first()
    if not op:
        raise NotFoundDomainError("بازشو مورد نظر یافت نشد.")
    get_tour_for_user(user=user, agency_id=agency_id, tour_id=op.wall.tour_id, require_edit=True)
    oid = str(op.id)
    op.delete()
    return {"deleted": True, "id": oid}


@transaction.atomic
def create_room_measurement(
    *,
    user: User,
    agency_id: Optional[UUID],
    room_id: UUID,
    label: str,
    start_point: list[float],
    end_point: list[float],
) -> RoomMeasurement:
    room = RoomGeometry.objects.select_related("tour", "tour__property").filter(id=room_id).first()
    if not room:
        raise NotFoundDomainError("اتاق مورد نظر یافت نشد.")
    get_tour_for_user(user=user, agency_id=agency_id, tour_id=room.tour_id, require_edit=True)
    dist = math.hypot(float(end_point[0]) - float(start_point[0]), float(end_point[1]) - float(start_point[1]))
    if dist < 0.05:
        raise ValidationDomainError("فاصله اندازه‌گیری باید حداقل ۵ سانتی‌متر باشد.")
    return RoomMeasurement.objects.create(
        room=room,
        label=label.strip()[:120] or "اندازه‌گیری داخلی",
        start_point=[round(float(start_point[0]), 3), round(float(start_point[1]), 3)],
        end_point=[round(float(end_point[0]), 3), round(float(end_point[1]), 3)],
        distance_m=Decimal(f"{dist:.3f}"),
        source="calibrated_floorplan",
        created_by=user,
    )


# ---------------------------------------------------------------------------
# Pure-Python / NumPy Ear-Clipping Polygon Triangulation + Watertight Prism
# ---------------------------------------------------------------------------

def _signed_area_2d(pts: list[tuple[float, float]]) -> float:
    s = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        s += x1 * y2 - x2 * y1
    return s * 0.5


def _point_in_triangle(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> bool:
    def _sign(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

    d1 = _sign(p, a, b)
    d2 = _sign(p, b, c)
    d3 = _sign(p, c, a)
    has_neg = (d1 < -1e-9) or (d2 < -1e-9) or (d3 < -1e-9)
    has_pos = (d1 > 1e-9) or (d2 > 1e-9) or (d3 > 1e-9)
    return not (has_neg and has_pos)


def _earclip_triangulate_2d(poly: list[tuple[float, float]]) -> list[tuple[int, int, int]]:
    pts = list(poly)
    if _signed_area_2d(pts) < 0:
        pts = list(reversed(pts))
        reversed_order = True
    else:
        reversed_order = False

    n = len(pts)
    indices = list(range(n))
    triangles: list[tuple[int, int, int]] = []
    guard = 0

    while len(indices) > 3 and guard < n * n:
        guard += 1
        ear_found = False
        m = len(indices)
        for i in range(m):
            i_prev = indices[(i - 1) % m]
            i_curr = indices[i]
            i_next = indices[(i + 1) % m]
            a, b, c = pts[i_prev], pts[i_curr], pts[i_next]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cross <= 1e-9:
                continue
            if any(
                _point_in_triangle(pts[idx], a, b, c)
                for idx in indices
                if idx not in (i_prev, i_curr, i_next)
            ):
                continue
            triangles.append((i_prev, i_curr, i_next))
            indices.pop(i)
            ear_found = True
            break
        if not ear_found:
            break

    if len(indices) == 3:
        triangles.append((indices[0], indices[1], indices[2]))

    if reversed_order:
        # Remap back to original poly order so vertex indices stay consistent
        triangles = [(n - 1 - a, n - 1 - b, n - 1 - c) for (a, b, c) in triangles]
    return triangles


def _build_extruded_room_slab_mesh(
    points_2d: list[list[float]],
    y_bottom: float,
    y_top: float,
    rgba: list[int],
) -> trimesh.Trimesh:
    poly = [(float(p[0]), float(p[1])) for p in points_2d]
    if _signed_area_2d(poly) < 0:
        poly = list(reversed(poly))
    n = len(poly)
    tris = _earclip_triangulate_2d(poly)
    if not tris:
        # Convex fan fallback if self-touching polygon
        tris = [(0, i, i + 1) for i in range(1, n - 1)]

    # Three.js Y-up coordinate mapping: 2D (x, y_plan) -> 3D (x, y_elevation, y_plan)
    verts_bot = [[x, y_bottom, z] for x, z in poly]
    verts_top = [[x, y_top, z] for x, z in poly]
    vertices = np.array(verts_bot + verts_top, dtype=np.float64)

    faces: list[list[int]] = []
    # Top cap (outward normal +Y)
    for a, b, c in tris:
        faces.append([n + a, n + c, n + b])
    # Bottom cap (outward normal -Y)
    for a, b, c in tris:
        faces.append([a, b, c])
    # Side walls around perimeter
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, n + j])
        faces.append([i, n + j, n + i])

    mesh = trimesh.Trimesh(vertices=vertices, faces=np.array(faces, dtype=np.int64), process=True)
    mesh.visual.vertex_colors = np.tile(np.array(rgba, dtype=np.uint8), (len(mesh.vertices), 1))
    return mesh


def _make_oriented_box(
    *,
    cx: float,
    cy: float,
    cz: float,
    length: float,
    height: float,
    thickness: float,
    yaw_rad: float,
    rgba: list[int],
) -> trimesh.Trimesh:
    box = trimesh.creation.box(extents=[max(0.02, length), max(0.02, height), max(0.02, thickness)])
    rot = trimesh.transformations.rotation_matrix(-yaw_rad, [0, 1, 0])
    trans = trimesh.transformations.translation_matrix([cx, cy, cz])
    box.apply_transform(trans @ rot)
    box.visual.vertex_colors = np.tile(np.array(rgba, dtype=np.uint8), (len(box.vertices), 1))
    return box


def _build_wall_with_openings_meshes(
    *,
    start_x: float,
    start_z: float,
    end_x: float,
    end_z: float,
    y_floor: float,
    wall_height: float,
    thickness: float,
    openings: list[WallOpening],
    wall_rgba: list[int],
    glass_rgba: list[int],
) -> list[trimesh.Trimesh]:
    dx = end_x - start_x
    dz = end_z - start_z
    total_len = math.hypot(dx, dz)
    if total_len < 0.05:
        return []
    ux, uz = dx / total_len, dz / total_len
    yaw_rad = math.atan2(dz, dx)

    def _span_mesh(s0: float, s1: float, y0: float, y1: float, rgba: list[int], th: float) -> Optional[trimesh.Trimesh]:
        seg_len = s1 - s0
        seg_h = y1 - y0
        if seg_len < 0.02 or seg_h < 0.02:
            return None
        mid_s = 0.5 * (s0 + s1)
        cx = start_x + ux * mid_s
        cz = start_z + uz * mid_s
        cy = y_floor + 0.5 * (y0 + y1)
        return _make_oriented_box(
            cx=cx,
            cy=cy,
            cz=cz,
            length=seg_len,
            height=seg_h,
            thickness=th,
            yaw_rad=yaw_rad,
            rgba=rgba,
        )

    if not openings:
        m = _span_mesh(0.0, total_len, 0.0, wall_height, wall_rgba, thickness)
        return [m] if m is not None else []

    sorted_ops = sorted(openings, key=lambda o: o.offset_ratio)
    meshes: list[trimesh.Trimesh] = []
    cursor = 0.0
    for op in sorted_ops:
        center_s = op.offset_ratio * total_len
        half_w = min(op.width_m * 0.5, total_len * 0.42)
        op_start = max(cursor, min(total_len - 0.05, center_s - half_w))
        op_end = max(op_start + 0.05, min(total_len, center_s + half_w))

        if op_start - cursor > 0.03:
            left_m = _span_mesh(cursor, op_start, 0.0, wall_height, wall_rgba, thickness)
            if left_m is not None:
                meshes.append(left_m)

        sill = max(0.0, min(wall_height - 0.25, float(op.sill_height_m)))
        op_top = min(wall_height - 0.05, sill + float(op.height_m))

        if sill > 0.03:
            sill_m = _span_mesh(op_start, op_end, 0.0, sill, wall_rgba, thickness)
            if sill_m is not None:
                meshes.append(sill_m)
        if wall_height - op_top > 0.03:
            lintel_m = _span_mesh(op_start, op_end, op_top, wall_height, wall_rgba, thickness)
            if lintel_m is not None:
                meshes.append(lintel_m)

        if op.kind in (WallOpening.Kind.WINDOW, WallOpening.Kind.BALCONY):
            pane = _span_mesh(op_start, op_end, sill, op_top, glass_rgba, max(0.03, thickness * 0.25))
            if pane is not None:
                meshes.append(pane)

        cursor = op_end

    if total_len - cursor > 0.03:
        right_m = _span_mesh(cursor, total_len, 0.0, wall_height, wall_rgba, thickness)
        if right_m is not None:
            meshes.append(right_m)

    return meshes


def build_parametric_dollhouse_glb(
    *,
    tour: VirtualTour,
    actor: Optional[User] = None,
    height_override_m: Optional[float] = None,
    thickness_override_m: Optional[float] = None,
) -> GeneratedModelAsset:
    """
    Constructs a real architectural 3D Dollhouse binary (.glb) from calibrated 2D rooms, walls & openings
    using Trimesh & NumPy. Every room pad carries metadata & node name encoding room_id and scene_id
    so the Three.js DollhouseViewer supports direct raycast navigation to the matching 360° panorama.
    """
    rooms = list(tour.room_geometries.select_related("floor", "scene").order_by("floor__order", "created_at"))
    walls = list(tour.wall_segments.select_related("floor").prefetch_related("openings").order_by("floor__order"))

    if not rooms and not walls:
        raise ValidationDomainError(
            "برای ساخت مدل سه‌بعدی Dollhouse حداقل یک اتاق روی پلان دو‌بعدی یا یک دیوار باید تعریف شده باشد."
        )

    bg = _sync_building_geometry(tour)
    default_h = float(height_override_m or bg.default_wall_height_m or 2.90)
    default_t = float(thickness_override_m or bg.default_wall_thickness_m or 0.18)
    slab_t = float(bg.slab_thickness_m or 0.22)

    # Compute building XY center so the 3D Dollhouse sits centered neatly at world origin (0, y, 0)
    all_pts = [pt for r in rooms for pt in (r.polygon_points or [])]
    for w in walls:
        all_pts.append([w.start_x, w.start_y])
        all_pts.append([w.end_x, w.end_y])
    xs = [float(p[0]) for p in all_pts]
    zs = [float(p[1]) for p in all_pts]
    center_x = 0.5 * (min(xs) + max(xs))
    center_z = 0.5 * (min(zs) + max(zs))

    scene_3d = trimesh.Scene()
    floors = list(tour.floors.order_by("order"))
    meshes_added = 0
    total_openings = 0

    wall_rgba = [226, 232, 240, 255]
    exterior_wall_rgba = [203, 213, 225, 255]
    glass_rgba = [125, 211, 252, 145]

    for idx_floor, floor in enumerate(floors):
        y_base = float(floor.elevation_m)
        floor_rooms = [r for r in rooms if r.floor_id == floor.id]
        floor_walls = [w for w in walls if w.floor_id == floor.id]

        for r_idx, room in enumerate(floor_rooms):
            pts_centered = [[float(p[0]) - center_x, float(p[1]) - center_z] for p in room.polygon_points]
            rgba = _hex_to_rgba(room.color_hex or ROOM_COLORS.get(room.room_type, "#0F766E"), 255)
            slab_mesh = _build_extruded_room_slab_mesh(pts_centered, y_base - slab_t, y_base, rgba)
            node_name = f"room__{room.id}__scene__{room.scene_id or 'none'}__floor__{floor.order}"
            scene_3d.add_geometry(slab_mesh, node_name=node_name, geom_name=f"geom_room_{idx_floor}_{r_idx}")
            meshes_added += 1

            # If no explicit wall segments exist on this floor, extrude perimeter walls automatically from room edges
            if not floor_walls:
                room_h = float(room.height_m or default_h)
                n_pts = len(pts_centered)
                for edge_i in range(n_pts):
                    p1 = pts_centered[edge_i]
                    p2 = pts_centered[(edge_i + 1) % n_pts]
                    edge_meshes = _build_wall_with_openings_meshes(
                        start_x=p1[0],
                        start_z=p1[1],
                        end_x=p2[0],
                        end_z=p2[1],
                        y_floor=y_base,
                        wall_height=room_h,
                        thickness=default_t * 0.75,
                        openings=[],
                        wall_rgba=wall_rgba,
                        glass_rgba=glass_rgba,
                    )
                    for m_i, wm in enumerate(edge_meshes):
                        scene_3d.add_geometry(
                            wm,
                            node_name=f"autowall__floor__{floor.order}__r{r_idx}__e{edge_i}_{m_i}",
                        )
                        meshes_added += 1

        for w_idx, wall in enumerate(floor_walls):
            ops = list(wall.openings.all())
            total_openings += len(ops)
            w_meshes = _build_wall_with_openings_meshes(
                start_x=wall.start_x - center_x,
                start_z=wall.start_y - center_z,
                end_x=wall.end_x - center_x,
                end_z=wall.end_y - center_z,
                y_floor=y_base,
                wall_height=float(wall.height_m or default_h),
                thickness=float(wall.thickness_m or default_t),
                openings=ops,
                wall_rgba=exterior_wall_rgba if wall.is_exterior else wall_rgba,
                glass_rgba=glass_rgba,
            )
            for part_i, wm in enumerate(w_meshes):
                scene_3d.add_geometry(wm, node_name=f"wall__{wall.id}__{part_i}__floor__{floor.order}")
                meshes_added += 1

    glb_bytes = scene_3d.export(file_type="glb")
    if not isinstance(glb_bytes, (bytes, bytearray)) or len(glb_bytes) < 64:
        raise ValidationDomainError("ساخت فایل باینری GLB مدل سه‌بعدی با خطا مواجه شد.")

    next_ver = (tour.generated_models.order_by("-version").values_list("version", flat=True).first() or 0) + 1
    storage = get_storage_provider()
    prefix = f"private/virtual_tours/{tour.agency_id}/{tour.id}/models/v{next_ver}"
    stored = storage.put_bytes(
        key_prefix=prefix,
        safe_filename=f"dollhouse-v{next_ver}.glb",
        content=bytes(glb_bytes),
        mime_type="model/gltf-binary",
    )

    bounds = {
        "min": [round(float(v), 3) for v in scene_3d.bounds[0]] if scene_3d.bounds is not None else [0, 0, 0],
        "max": [round(float(v), 3) for v in scene_3d.bounds[1]] if scene_3d.bounds is not None else [0, 0, 0],
        "center_offset_m": [round(center_x, 3), round(center_z, 3)],
    }

    with transaction.atomic():
        prior_current = tour.generated_models.filter(is_current=True).first()
        has_approved = prior_current and prior_current.state == GeneratedModelAsset.State.APPROVED
        if not has_approved:
            tour.generated_models.filter(is_current=True).update(
                is_current=False, state=GeneratedModelAsset.State.SUPERSEDED
            )

        asset = GeneratedModelAsset.objects.create(
            tour=tour,
            version=next_ver,
            format="glb",
            state=GeneratedModelAsset.State.READY,
            geometry_source="floorplan_2d_extrusion",
            estimated_accuracy="تقریبی (برگرفته از پلان دو‌بعدی کالیبره‌شده)",
            total_area_sqm=bg.total_area_sqm,
            storage_key=stored.file_key,
            size_bytes=stored.size_bytes,
            is_current=not has_approved,
            metadata={
                "engine": "trimesh_parametric",
                "meshes_count": meshes_added,
                "floors_count": len(floors),
                "rooms_count": len(rooms),
                "walls_count": len(walls),
                "openings_count": total_openings,
                "bounds": bounds,
            },
            created_by=actor,
            updated_by=actor,
        )

    return asset


def execute_dollhouse_build_job(*, job_id: UUID) -> GeneratedModelAsset:
    job = ProcessingJob.objects.select_related("tour").get(id=job_id)
    if job.state == ProcessingJob.State.CANCELLED:
        raise ValidationDomainError("پردازش ساخت مدل سه‌بعدی لغو شده است.")

    job.state = ProcessingJob.State.RUNNING
    job.started_at = timezone.now()
    job.progress = 15
    job.current_step = "استخراج هندسه طبقات و دیوارها از پلان کالیبره‌شده"
    job.save(update_fields=["state", "started_at", "progress", "current_step", "updated_at"])

    try:
        params = job.input_params or {}
        asset = build_parametric_dollhouse_glb(
            tour=job.tour,
            actor=job.created_by,
            height_override_m=params.get("wall_height_m"),
            thickness_override_m=params.get("wall_thickness_m"),
        )
        job.state = ProcessingJob.State.SUCCEEDED
        job.progress = 100
        job.current_step = "مدل سه‌بعدی Dollhouse (GLB) با موفقیت ساخته شد"
        job.completed_at = timezone.now()
        job.result = {
            "model_asset_id": str(asset.id),
            "version": asset.version,
            "size_bytes": asset.size_bytes,
            "total_area_sqm": str(asset.total_area_sqm),
            "geometry_source": asset.geometry_source,
        }
        job.save(update_fields=["state", "progress", "current_step", "completed_at", "result", "updated_at"])
        return asset
    except Exception as exc:
        job.state = ProcessingJob.State.FAILED
        job.error = str(exc)
        job.completed_at = timezone.now()
        job.current_step = "خطا در ساخت مدل سه‌بعدی"
        job.save(update_fields=["state", "error", "completed_at", "current_step", "updated_at"])
        raise


def enqueue_dollhouse_build(
    *,
    user: User,
    agency_id: Optional[UUID],
    tour_id: UUID,
    wall_height_m: Optional[float] = None,
    wall_thickness_m: Optional[float] = None,
) -> ProcessingJob:
    tour = get_tour_for_user(user=user, agency_id=agency_id, tour_id=tour_id, require_edit=True)
    if not tour.room_geometries.exists() and not tour.wall_segments.exists():
        raise ValidationDomainError(
            "ابتدا حداقل یک اتاق یا دیوار روی پلان دو‌بعدی ثبت کنید، سپس ساخت مدل سه‌بعدی را اجرا نمایید."
        )

    active = ProcessingJob.objects.filter(
        tour=tour,
        job_type=ProcessingJob.JobType.MODEL_BUILD,
        state__in=[ProcessingJob.State.QUEUED, ProcessingJob.State.RUNNING],
    ).first()
    if active:
        raise ConflictDomainError("ساخت مدل سه‌بعدی هم‌اکنون در حال اجرا است.")

    job = ProcessingJob.objects.create(
        tour=tour,
        job_type=ProcessingJob.JobType.MODEL_BUILD,
        state=ProcessingJob.State.QUEUED,
        progress=0,
        current_step="در صف ساخت مدل سه‌بعدی Dollhouse",
        input_params={
            "wall_height_m": wall_height_m,
            "wall_thickness_m": wall_thickness_m,
        },
        created_by=user,
        updated_by=user,
    )
    record_audit_event(
        action="virtual_tour.model_build_enqueue",
        resource_type="ProcessingJob",
        resource_id=str(job.id),
        actor=user,
        agency_id=tour.agency_id,
        after_state={"tour_id": str(tour.id)},
    )

    from apps.virtual_tours.services.panorama_service import _has_active_celery_worker
    from apps.virtual_tours.tasks.jobs import build_3d_model_task

    if _has_active_celery_worker():
        res = build_3d_model_task.delay(str(job.id))
        job.celery_task_id = str(res.id)
        job.save(update_fields=["celery_task_id", "updated_at"])
    else:
        build_3d_model_task.apply(args=[str(job.id)]).get()
        job.refresh_from_db()

    return job


@transaction.atomic
def review_generated_model(
    *,
    user: User,
    agency_id: Optional[UUID],
    model_id: UUID,
    approve: bool,
    reason: str = "",
) -> GeneratedModelAsset:
    asset = GeneratedModelAsset.objects.select_related("tour", "tour__property").filter(id=model_id).first()
    if not asset:
        raise NotFoundDomainError("مدل سه‌بعدی مورد نظر یافت نشد.")
    assert_tour_approve_access(user=user, agency_id=agency_id, prop=asset.tour.property)
    if asset.state == GeneratedModelAsset.State.FAILED:
        raise ValidationDomainError("نسخه ناموفق مدل قابل تأیید نیست.")

    if approve:
        asset.tour.generated_models.exclude(id=asset.id).filter(is_current=True).update(
            is_current=False, state=GeneratedModelAsset.State.SUPERSEDED
        )
        asset.state = GeneratedModelAsset.State.APPROVED
        asset.is_current = True
    else:
        asset.state = GeneratedModelAsset.State.REJECTED
    asset.updated_by = user
    asset.save(update_fields=["state", "is_current", "updated_by", "updated_at"])

    ModelReview.objects.create(
        model_asset=asset,
        decision=ModelReview.Decision.APPROVED if approve else ModelReview.Decision.REJECTED,
        reviewer=user,
        reason=(reason or "").strip(),
        reviewed_at=timezone.now(),
        created_by=user,
    )
    record_audit_event(
        action="virtual_tour.model_review",
        resource_type="GeneratedModelAsset",
        resource_id=str(asset.id),
        actor=user,
        agency_id=asset.tour.agency_id,
        after_state={"version": asset.version, "state": asset.state, "approve": approve},
    )
    return asset


@transaction.atomic
def restore_generated_model(
    *,
    user: User,
    agency_id: Optional[UUID],
    model_id: UUID,
) -> GeneratedModelAsset:
    asset = GeneratedModelAsset.objects.select_related("tour", "tour__property").filter(id=model_id).first()
    if not asset:
        raise NotFoundDomainError("نسخه مدل سه‌بعدی یافت نشد.")
    get_tour_for_user(user=user, agency_id=agency_id, tour_id=asset.tour_id, require_edit=True)
    if asset.state == GeneratedModelAsset.State.FAILED:
        raise ValidationDomainError("نسخه ناموفق قابل بازیابی نیست.")

    asset.tour.generated_models.exclude(id=asset.id).filter(is_current=True).update(
        is_current=False, state=GeneratedModelAsset.State.SUPERSEDED
    )
    asset.is_current = True
    if asset.state == GeneratedModelAsset.State.SUPERSEDED:
        asset.state = (
            GeneratedModelAsset.State.APPROVED
            if asset.reviews.filter(decision=ModelReview.Decision.APPROVED).exists()
            else GeneratedModelAsset.State.READY
        )
    asset.updated_by = user
    asset.save(update_fields=["is_current", "state", "updated_by", "updated_at"])
    return asset
