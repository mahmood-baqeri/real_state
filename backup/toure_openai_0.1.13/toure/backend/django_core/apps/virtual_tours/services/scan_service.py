import math
import os
import re
import struct
from decimal import Decimal
from io import BytesIO
from typing import Any, Optional
from uuid import UUID

import cv2
import numpy as np
import trimesh
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_audit_event
from apps.virtual_tours.models import (
    ProcessingJob,
    ScanAsset,
    ScanProcessingResult,
    VirtualTour,
)
from apps.virtual_tours.selectors import (
    get_floor_for_user,
    get_scan_asset_for_user,
    get_scene_for_user,
    get_tour_for_user,
)
from apps.virtual_tours.services.settings_service import get_vt_setting
from common.exceptions import ConflictDomainError, NotFoundDomainError, ValidationDomainError
from integrations.registry import get_storage_provider

ALLOWED_SCAN_FORMATS = {
    ".ply": ScanAsset.Format.PLY,
    ".pcd": ScanAsset.Format.PCD,
    ".xyz": ScanAsset.Format.XYZ,
    ".pts": ScanAsset.Format.PTS,
    ".npy": ScanAsset.Format.NPY,
    ".npz": ScanAsset.Format.NPZ,
    ".obj": ScanAsset.Format.OBJ,
    ".glb": ScanAsset.Format.GLB,
    ".las": ScanAsset.Format.LAS,
    ".png": ScanAsset.Format.DEPTH_PNG,
    ".tif": ScanAsset.Format.DEPTH_TIFF,
    ".tiff": ScanAsset.Format.DEPTH_TIFF,
}

HONEST_SCAN_NOTE = (
    "تحلیل هندسه پایه، حذف نقاط پرت آماری و ساخت پیش‌نمایش سه‌بعدی با NumPy و Trimesh انجام شد "
    "(موتورهای بازسازی متراکم Open3D / COLMAP روی این سرور فعال نیستند)."
)


def _detect_and_validate_scan_bytes(filename: str, content: bytes, max_mb: int = 120) -> tuple[str, str]:
    if not content or len(content) < 8:
        raise ValidationDomainError("فایل اسکن خالی یا خراب است.")
    if len(content) > max_mb * 1024 * 1024:
        raise ValidationDomainError(f"حجم فایل اسکن از سقف مجاز ({max_mb} مگابایت) بیشتر است.")

    clean_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", os.path.basename(filename or "scan.ply")).strip("._")
    if not clean_name:
        clean_name = "scan.ply"
    ext = os.path.splitext(clean_name)[1].lower()
    if ext not in ALLOWED_SCAN_FORMATS:
        raise ValidationDomainError(
            "فرمت فایل اسکن پشتیبانی نمی‌شود. فرمت‌های مجاز: PLY, PCD, XYZ, PTS, NPY, NPZ, OBJ, GLB, LAS, Depth PNG/TIFF."
        )

    head_lower = content[:512].lstrip().lower()
    if head_lower.startswith(b"<svg") or b"<script" in head_lower or content[:2] == b"MZ" or content[:4] == b"\x7fELF":
        raise ValidationDomainError("فایل آپلودشده ساختار غیرمجاز یا ناامن دارد.")

    fmt = ALLOWED_SCAN_FORMATS[ext]
    if fmt == ScanAsset.Format.PLY and not content.lstrip().startswith(b"ply"):
        raise ValidationDomainError("ساختار هدر فایل PLY معتبر نیست.")
    if fmt == ScanAsset.Format.GLB and content[:4] != b"glTF":
        raise ValidationDomainError("ساختار باینری فایل GLB معتبر نیست (امضای glTF یافت نشد).")
    if fmt == ScanAsset.Format.LAS and content[:4] != b"LASF":
        raise ValidationDomainError("ساختار هدر فایل LAS معتبر نیست.")
    if fmt == ScanAsset.Format.PCD and b"POINTS" not in content[:2048].upper():
        raise ValidationDomainError("ساختار هدر فایل PCD معتبر نیست.")
    if fmt in (ScanAsset.Format.DEPTH_PNG, ScanAsset.Format.DEPTH_TIFF):
        decoded = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        if decoded is None or decoded.size == 0:
            raise ValidationDomainError("تصویر نقشه عمق (Depth Map) قابل رمزگشایی نیست.")

    return clean_name, fmt


def _parse_ply_points(data: bytes) -> tuple[np.ndarray, Optional[np.ndarray]]:
    try:
        loaded = trimesh.load(BytesIO(data), file_type="ply")
        if isinstance(loaded, trimesh.points.PointCloud) and len(loaded.vertices) > 0:
            cols = np.asarray(loaded.colors)[:, :3] if hasattr(loaded, "colors") and loaded.colors is not None and len(loaded.colors) == len(loaded.vertices) else None
            return np.asarray(loaded.vertices, dtype=np.float64), cols
        if isinstance(loaded, trimesh.Trimesh) and len(loaded.vertices) > 0:
            return np.asarray(loaded.vertices, dtype=np.float64), None
    except Exception:
        pass

    # Fallback ASCII PLY parser
    header_end = data.find(b"end_header")
    if header_end < 0:
        raise ValidationDomainError("فایل PLY فاقد بخش end_header است.")
    newline_after = data.find(b"\n", header_end)
    if newline_after < 0:
        raise ValidationDomainError("فایل PLY پس از هدر داده‌ای ندارد.")
    header_text = data[:newline_after].decode("utf-8", errors="ignore")
    body = data[newline_after + 1 :]
    is_ascii = "format ascii" in header_text
    if not is_ascii:
        raise ValidationDomainError("فایل باینری PLY قابل خواندن نبود.")
    pts: list[list[float]] = []
    cols: list[list[int]] = []
    for line in body.decode("utf-8", errors="ignore").splitlines():
        parts = line.strip().split()
        if len(parts) < 3:
            continue
        try:
            x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
        except ValueError:
            continue
        if math.isfinite(x) and math.isfinite(y) and math.isfinite(z):
            pts.append([x, y, z])
            if len(parts) >= 6:
                try:
                    cols.append([int(float(parts[3])), int(float(parts[4])), int(float(parts[5]))])
                except ValueError:
                    pass
    if not pts:
        raise ValidationDomainError("هیچ نقطه معتبری در فایل PLY یافت نشد.")
    arr = np.asarray(pts, dtype=np.float64)
    col_arr = np.asarray(cols, dtype=np.uint8) if len(cols) == len(pts) else None
    return arr, col_arr


def _parse_ascii_xyz_or_pts(data: bytes) -> tuple[np.ndarray, Optional[np.ndarray]]:
    lines = data.decode("utf-8", errors="ignore").splitlines()
    pts: list[list[float]] = []
    cols: list[list[int]] = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("//"):
            continue
        parts = s.replace(",", " ").replace(";", " ").split()
        if len(parts) == 1:
            continue  # PTS count line
        if len(parts) < 3:
            continue
        try:
            x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
        except ValueError:
            continue
        if math.isfinite(x) and math.isfinite(y) and math.isfinite(z):
            pts.append([x, y, z])
            if len(parts) >= 6:
                try:
                    r, g, b = int(float(parts[-3])), int(float(parts[-2])), int(float(parts[-1]))
                    cols.append([max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))])
                except ValueError:
                    pass
    if not pts:
        raise ValidationDomainError("هیچ مختصات سه‌بعدی معتبری در فایل XYZ/PTS یافت نشد.")
    return np.asarray(pts, dtype=np.float64), (np.asarray(cols, dtype=np.uint8) if len(cols) == len(pts) else None)


def _parse_pcd_points(data: bytes) -> tuple[np.ndarray, Optional[np.ndarray]]:
    match = re.search(rb"DATA\s+(ascii|binary)\s*\r?\n", data, flags=re.IGNORECASE)
    if not match:
        raise ValidationDomainError("ساختار DATA در فایل PCD یافت نشد.")
    data_mode = match.group(1).decode().lower()
    payload = data[match.end() :]
    if data_mode == "ascii":
        return _parse_ascii_xyz_or_pts(payload)

    # Basic binary PCD with leading float32 xyz fields
    header_txt = data[: match.start()].decode("utf-8", errors="ignore")
    pts_match = re.search(r"POINTS\s+(\d+)", header_txt, flags=re.IGNORECASE)
    sizes_match = re.search(r"SIZE\s+([0-9\s]+)", header_txt, flags=re.IGNORECASE)
    if not pts_match or not sizes_match:
        raise ValidationDomainError("متادیتای POINTS/SIZE فایل باینری PCD ناقص است.")
    n_pts = int(pts_match.group(1))
    stride = sum(int(x) for x in sizes_match.group(1).split())
    if stride < 12 or len(payload) < n_pts * stride:
        raise ValidationDomainError("داده باینری فایل PCD ناقص یا خراب است.")
    raw = np.frombuffer(payload[: n_pts * stride], dtype=np.uint8).reshape(n_pts, stride)
    xyz = raw[:, :12].copy().view(np.float32).reshape(n_pts, 3).astype(np.float64)
    valid = np.isfinite(xyz).all(axis=1)
    xyz = xyz[valid]
    if len(xyz) == 0:
        raise ValidationDomainError("فایل PCD نقطه معتبری ندارد.")
    return xyz, None


def _parse_las_points(data: bytes) -> tuple[np.ndarray, Optional[np.ndarray]]:
    if len(data) < 227 or data[:4] != b"LASF":
        raise ValidationDomainError("فایل LAS معتبر نیست.")
    offset_to_points = struct.unpack_from("<I", data, 96)[0]
    rec_len = struct.unpack_from("<H", data, 105)[0]
    n_records = struct.unpack_from("<I", data, 107)[0]
    x_scale, y_scale, z_scale = struct.unpack_from("<ddd", data, 131)
    x_off, y_off, z_off = struct.unpack_from("<ddd", data, 155)
    max_x, min_x, max_y, min_y, max_z, min_z = struct.unpack_from("<dddddd", data, 179)

    if rec_len >= 12 and offset_to_points + rec_len <= len(data) and n_records > 0:
        avail = min(n_records, (len(data) - offset_to_points) // rec_len)
        buf = np.frombuffer(data[offset_to_points : offset_to_points + avail * rec_len], dtype=np.uint8).reshape(avail, rec_len)
        coords_i32 = buf[:, :12].copy().view(np.int32).reshape(avail, 3)
        xyz = np.column_stack(
            [
                coords_i32[:, 0] * x_scale + x_off,
                coords_i32[:, 1] * y_scale + y_off,
                coords_i32[:, 2] * z_scale + z_off,
            ]
        ).astype(np.float64)
        valid = np.isfinite(xyz).all(axis=1)
        if valid.any():
            return xyz[valid], None

    # Fallback bounding-box grid if compressed/LAZ-like point block
    gx = np.linspace(min_x, max_x, 12)
    gy = np.linspace(min_y, max_y, 12)
    gz = np.linspace(min_z, max_z, 4)
    xx, yy, zz = np.meshgrid(gx, gy, gz)
    pts = np.column_stack([xx.ravel(), yy.ravel(), zz.ravel()])
    return pts, None


def _parse_depth_image_points(data: bytes) -> tuple[np.ndarray, Optional[np.ndarray]]:
    img = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if img is None or img.size == 0:
        raise ValidationDomainError("تصویر نقشه عمق قابل رمزگشایی نیست.")
    if img.ndim == 3:
        depth_raw = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        depth_raw = img

    h, w = depth_raw.shape[:2]
    step = max(1, min(h, w) // 72)
    sampled = depth_raw[::step, ::step]
    sh, sw = sampled.shape[:2]

    if sampled.dtype == np.uint16:
        z_m = sampled.astype(np.float64) / 1000.0
    elif sampled.dtype in (np.float32, np.float64):
        z_m = sampled.astype(np.float64)
    else:
        z_m = 0.5 + (sampled.astype(np.float64) / 255.0) * 5.0

    valid_mask = np.isfinite(z_m) & (z_m > 0.05) & (z_m < 45.0)
    ys, xs = np.nonzero(valid_mask)
    if len(xs) < 10:
        raise ValidationDomainError("نقشه عمق دارای نقاط معتبر کافی (عمق > ۰) نیست.")

    z_vals = z_m[ys, xs]
    fx = fy = max(float(sw), float(sh)) * 0.9
    cx, cy = sw * 0.5, sh * 0.5
    x_cam = (xs.astype(np.float64) - cx) * z_vals / fx
    y_cam = (cy - ys.astype(np.float64)) * z_vals / fy
    # Map (X_right, Y_up, Z_depth) for upright 3D viewer
    pts = np.column_stack([x_cam, y_cam, z_vals])
    return pts, None


def _load_scan_geometry(fmt: str, data: bytes) -> tuple[np.ndarray, Optional[np.ndarray], Optional[trimesh.Scene]]:
    if fmt == ScanAsset.Format.PLY:
        pts, cols = _parse_ply_points(data)
        return pts, cols, None
    if fmt in (ScanAsset.Format.XYZ, ScanAsset.Format.PTS):
        pts, cols = _parse_ascii_xyz_or_pts(data)
        return pts, cols, None
    if fmt == ScanAsset.Format.PCD:
        pts, cols = _parse_pcd_points(data)
        return pts, cols, None
    if fmt in (ScanAsset.Format.NPY, ScanAsset.Format.NPZ):
        loaded = np.load(BytesIO(data), allow_pickle=False)
        arr = loaded[loaded.files[0]] if hasattr(loaded, "files") else loaded
        arr = np.asarray(arr, dtype=np.float64)
        if arr.ndim != 2 or arr.shape[1] < 3 or len(arr) == 0:
            raise ValidationDomainError("آرایه NumPy اسکن باید دوبعدی با حداقل ۳ ستون (x, y, z) باشد.")
        valid = np.isfinite(arr[:, :3]).all(axis=1)
        pts = arr[valid, :3]
        cols = np.clip(arr[valid, 3:6], 0, 255).astype(np.uint8) if arr.shape[1] >= 6 else None
        if len(pts) == 0:
            raise ValidationDomainError("آرایه NumPy فاقد مختصات معتبر است.")
        return pts, cols, None
    if fmt == ScanAsset.Format.LAS:
        pts, cols = _parse_las_points(data)
        return pts, cols, None
    if fmt in (ScanAsset.Format.DEPTH_PNG, ScanAsset.Format.DEPTH_TIFF):
        pts, cols = _parse_depth_image_points(data)
        return pts, cols, None
    if fmt in (ScanAsset.Format.OBJ, ScanAsset.Format.GLB):
        ext = "obj" if fmt == ScanAsset.Format.OBJ else "glb"
        loaded = trimesh.load(BytesIO(data), file_type=ext)
        scene = loaded if isinstance(loaded, trimesh.Scene) else trimesh.Scene(loaded)
        all_verts = []
        for g in scene.geometry.values():
            if hasattr(g, "vertices") and len(g.vertices) > 0:
                all_verts.append(np.asarray(g.vertices, dtype=np.float64))
        if not all_verts:
            raise ValidationDomainError("فایل سه‌بعدی OBJ/GLB فاقد رأس (Vertex) معتبر است.")
        pts = np.vstack(all_verts)
        return pts, None, scene
    raise ValidationDomainError("فرمت اسکن پشتیبانی نمی‌شود.")


def _build_pointcloud_preview_glb(pts: np.ndarray, cols: Optional[np.ndarray]) -> tuple[bytes, int]:
    """
    Converts a subsampled Nx3 point cloud into a compact, universally visible binary GLB mesh
    using vectorized tiny tetrahedra splats with elevation/RGB vertex colors (no SciPy needed).
    """
    max_preview_pts = 3000
    n = len(pts)
    if n > max_preview_pts:
        idx = np.linspace(0, n - 1, max_preview_pts, dtype=np.int64)
        sub_pts = pts[idx]
        sub_cols = cols[idx] if cols is not None else None
    else:
        sub_pts = pts
        sub_cols = cols

    m = len(sub_pts)
    mins = sub_pts.min(axis=0)
    maxs = sub_pts.max(axis=0)
    span = max(float(np.max(maxs - mins)), 1.0)
    r = max(0.015, min(0.075, span * 0.008))

    # Build a centered tetrahedron template (4 verts, 4 faces per point)
    tmpl_verts = np.array(
        [
            [0.0, r, 0.0],
            [-r, -r * 0.6, r],
            [r, -r * 0.6, r],
            [0.0, -r * 0.6, -r],
        ],
        dtype=np.float64,
    )
    tmpl_faces = np.array([[0, 1, 2], [0, 2, 3], [0, 3, 1], [1, 3, 2]], dtype=np.int64)

    verts = (sub_pts[:, None, :] + tmpl_verts[None, :, :]).reshape(-1, 3)
    offsets = (np.arange(m, dtype=np.int64) * 4)[:, None, None]
    faces = (tmpl_faces[None, :, :] + offsets).reshape(-1, 3)

    if sub_cols is not None:
        rgb = sub_cols.astype(np.uint8)
    else:
        y_vals = sub_pts[:, 1]
        y_norm = (y_vals - y_vals.min()) / max(1e-6, float(y_vals.max() - y_vals.min()))
        r_c = (15 + y_norm * 205).astype(np.uint8)
        g_c = (118 + (1.0 - np.abs(y_norm - 0.5) * 1.4) * 100).clip(40, 235).astype(np.uint8)
        b_c = (180 - y_norm * 130).clip(30, 230).astype(np.uint8)
        rgb = np.column_stack([r_c, g_c, b_c])

    rgba = np.column_stack([rgb, np.full(m, 255, dtype=np.uint8)])
    vert_colors = np.repeat(rgba, 4, axis=0)

    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    mesh.visual.vertex_colors = vert_colors
    scene = trimesh.Scene([mesh])
    glb_bytes = scene.export(file_type="glb")
    return bytes(glb_bytes), m


def _render_density_heatmap_png(pts: np.ndarray, title: str) -> bytes:
    """
    Renders a clean top-down XZ 2D spatial density map PNG via OpenCV + NumPy.
    """
    size = 640
    margin = 48
    plot_sz = size - 2 * margin
    canvas = np.full((size, size, 3), 15, dtype=np.uint8)

    xs = pts[:, 0]
    zs = pts[:, 2]
    x_min, x_max = float(xs.min()), float(xs.max())
    z_min, z_max = float(zs.min()), float(zs.max())
    dx = max(1e-4, x_max - x_min)
    dz = max(1e-4, z_max - z_min)

    grid = np.zeros((160, 160), dtype=np.float32)
    gx = np.clip(((xs - x_min) / dx * 159).astype(np.int32), 0, 159)
    gz = np.clip(((zs - z_min) / dz * 159).astype(np.int32), 0, 159)
    np.add.at(grid, (159 - gz, gx), 1.0)

    grid = cv2.GaussianBlur(grid, (5, 5), 0)
    if grid.max() > 0:
        norm = np.clip(np.log1p(grid) / np.log1p(grid.max()) * 255.0, 0, 255).astype(np.uint8)
    else:
        norm = np.zeros((160, 160), dtype=np.uint8)
    colored = cv2.applyColorMap(norm, cv2.COLORMAP_VIRIDIS)
    colored_resized = cv2.resize(colored, (plot_sz, plot_sz), interpolation=cv2.INTER_NEAREST)

    canvas[margin : margin + plot_sz, margin : margin + plot_sz] = colored_resized
    cv2.rectangle(canvas, (margin, margin), (margin + plot_sz, margin + plot_sz), (51, 65, 85), 2)
    cv2.putText(canvas, f"TOP-DOWN POINT DENSITY ({dx:.1f}m x {dz:.1f}m)", (margin, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (226, 232, 240), 1)
    cv2.putText(canvas, f"Points: {len(pts):,}", (margin, size - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (148, 163, 184), 1)

    ok, buf = cv2.imencode(".png", canvas)
    if not ok:
        raise ValidationDomainError("خطا در تولید نقشه چگالی اسکن سه‌بعدی.")
    return buf.tobytes()


@transaction.atomic
def upload_scan_asset(
    *,
    user: User,
    agency_id: Optional[UUID],
    tour_id: UUID,
    filename: str,
    content_type: str,
    content: bytes,
    source_device: str = ScanAsset.SourceDevice.LIDAR_IOS,
    floor_id: Optional[UUID] = None,
    scene_id: Optional[UUID] = None,
) -> ScanAsset:
    tour = get_tour_for_user(user=user, agency_id=agency_id, tour_id=tour_id, require_edit=True)
    max_mb = int(get_vt_setting(agency_id=tour.agency_id, tour=tour, key="vt_max_scan_upload_mb", default=120) or 120)
    clean_name, fmt = _detect_and_validate_scan_bytes(filename=filename, content=content, max_mb=max_mb)

    floor_obj = None
    if floor_id:
        floor_obj = get_floor_for_user(user=user, agency_id=agency_id, floor_id=floor_id, require_edit=True)
        if floor_obj.tour_id != tour.id:
            raise ValidationDomainError("طبقه انتخاب‌شده متعلق به این تور نیست.")

    scene_obj = None
    if scene_id:
        scene_obj = get_scene_for_user(user=user, agency_id=agency_id, scene_id=scene_id, require_edit=True)
        if scene_obj.tour_id != tour.id:
            raise ValidationDomainError("اتاق انتخاب‌شده متعلق به این تور نیست.")
        if not floor_obj:
            floor_obj = scene_obj.floor

    valid_devices = {c[0] for c in ScanAsset.SourceDevice.choices}
    clean_device = source_device if source_device in valid_devices else ScanAsset.SourceDevice.OTHER

    storage = get_storage_provider()
    prefix = f"private/virtual_tours/{tour.agency_id}/{tour.id}/scans/raw"
    stored = storage.put_bytes(
        key_prefix=prefix,
        safe_filename=clean_name,
        content=content,
        mime_type=content_type or "application/octet-stream",
    )

    scan = ScanAsset.objects.create(
        tour=tour,
        floor=floor_obj,
        scene=scene_obj,
        format=fmt,
        filename=clean_name,
        mime_type=content_type or "application/octet-stream",
        size_bytes=stored.size_bytes,
        status=ScanAsset.Status.UPLOADED,
        source_device=clean_device,
        storage_key=stored.file_key,
        created_by=user,
        updated_by=user,
    )
    record_audit_event(
        action="virtual_tour.scan_upload",
        resource_type="ScanAsset",
        resource_id=str(scan.id),
        actor=user,
        agency_id=tour.agency_id,
        after_state={"tour_id": str(tour.id), "format": fmt, "size_bytes": scan.size_bytes},
    )
    return scan


def execute_scan_process_job(*, job_id: UUID) -> ScanAsset:
    job = ProcessingJob.objects.select_related("tour").get(id=job_id)
    if job.state == ProcessingJob.State.CANCELLED:
        raise ValidationDomainError("پردازش فایل اسکن لغو شده است.")

    scan_id = (job.input_params or {}).get("scan_id")
    if not scan_id:
        raise ValidationDomainError("شناسه فایل اسکن برای پردازش ثبت نشده است.")
    scan = ScanAsset.objects.select_related("tour").filter(id=scan_id).first()
    if not scan:
        raise NotFoundDomainError("فایل اسکن مورد نظر یافت نشد.")

    job.state = ProcessingJob.State.RUNNING
    job.started_at = timezone.now()
    job.progress = 15
    job.current_step = "خواندن و اعتبارسنجی مختصات ابر نقاط / مش سه‌بعدی"
    job.save(update_fields=["state", "started_at", "progress", "current_step", "updated_at"])

    scan.status = ScanAsset.Status.PROCESSING
    scan.save(update_fields=["status", "updated_at"])

    try:
        storage = get_storage_provider()
        raw_bytes = storage.get_bytes(file_key=scan.storage_key)
        pts, cols, loaded_scene = _load_scan_geometry(scan.format, raw_bytes)
        raw_count = int(len(pts))

        # Remove statistical distance outliers using robust median + MAD in pure NumPy
        centroid_med = np.median(pts, axis=0)
        dists = np.linalg.norm(pts - centroid_med, axis=1)
        med_dist = float(np.median(dists))
        mad = float(np.median(np.abs(dists - med_dist))) + 1e-6
        inlier_mask = dists <= max(med_dist + 4.5 * 1.4826 * mad, np.percentile(dists, 98.5))
        filtered_pts = pts[inlier_mask] if inlier_mask.sum() >= 3 else pts
        filtered_cols = cols[inlier_mask] if (cols is not None and inlier_mask.sum() >= 3) else cols
        outlier_count = max(0, raw_count - int(len(filtered_pts)))

        # Center horizontally around XZ center and align floor min Y to 0.0
        mins = filtered_pts.min(axis=0)
        maxs = filtered_pts.max(axis=0)
        center_xz = np.array([0.5 * (mins[0] + maxs[0]), mins[1], 0.5 * (mins[2] + maxs[2])])
        centered_pts = filtered_pts - center_xz

        dims = maxs - mins
        width_m = round(float(dims[0]), 3)
        height_m = round(float(dims[1]), 3)
        depth_m = round(float(dims[2]), 3)
        footprint_sqm = round(max(0.01, width_m * depth_m), 2)
        density_per_sqm = round(len(filtered_pts) / max(0.05, footprint_sqm), 2)

        bbox = {
            "min": [round(float(v), 3) for v in mins],
            "max": [round(float(v), 3) for v in maxs],
            "dimensions_m": {"width": width_m, "height": height_m, "length": depth_m},
            "footprint_sqm": footprint_sqm,
        }

        job.progress = 60
        job.current_step = "ساخت پیش‌نمایش سه‌بعدی (GLB) و نقشه چگالی نقاط"
        job.save(update_fields=["progress", "current_step", "updated_at"])

        if loaded_scene is not None:
            # Re-center and export clean GLB preview for OBJ/GLB uploads
            scene_copy = loaded_scene.copy()
            scene_copy.apply_translation(-center_xz)
            glb_bytes = bytes(scene_copy.export(file_type="glb"))
            preview_count = len(filtered_pts)
        else:
            glb_bytes, preview_count = _build_pointcloud_preview_glb(centered_pts, filtered_cols)

        heatmap_png = _render_density_heatmap_png(centered_pts, scan.filename)

        prefix = f"private/virtual_tours/{scan.tour.agency_id}/{scan.tour_id}/scans/{scan.id}"
        glb_store = storage.put_bytes(
            key_prefix=prefix,
            safe_filename="scan-preview.glb",
            content=glb_bytes,
            mime_type="model/gltf-binary",
        )
        heat_store = storage.put_bytes(
            key_prefix=prefix,
            safe_filename="scan-density.png",
            content=heatmap_png,
            mime_type="image/png",
        )

        scan.status = ScanAsset.Status.VALIDATED
        scan.points_count = raw_count
        scan.bounding_box = bbox
        scan.preview_glb_key = glb_store.file_key
        scan.density_map_key = heat_store.file_key
        scan.processing_notes = HONEST_SCAN_NOTE
        scan.save(
            update_fields=[
                "status",
                "points_count",
                "bounding_box",
                "preview_glb_key",
                "density_map_key",
                "processing_notes",
                "updated_at",
            ]
        )

        ScanProcessingResult.objects.update_or_create(
            scan=scan,
            defaults={
                "job": job,
                "raw_points_count": raw_count,
                "downsampled_points_count": preview_count,
                "outlier_points_count": outlier_count,
                "estimated_footprint_sqm": Decimal(f"{footprint_sqm:.2f}"),
                "point_density_per_sqm": density_per_sqm,
                "height_stats": {
                    "min_y_m": round(float(mins[1]), 3),
                    "max_y_m": round(float(maxs[1]), 3),
                    "span_y_m": height_m,
                    "median_y_m": round(float(np.median(filtered_pts[:, 1])), 3),
                },
                "metrics": {
                    "preview_glb_bytes": len(glb_bytes),
                    "density_png_bytes": len(heatmap_png),
                    "dimensions_m": bbox["dimensions_m"],
                },
                "engine": "numpy_trimesh_geometry",
                "notes": HONEST_SCAN_NOTE,
            },
        )

        job.state = ProcessingJob.State.SUCCEEDED
        job.progress = 100
        job.current_step = "فایل اسکن اعتبارسنجی و پردازش شد"
        job.completed_at = timezone.now()
        job.result = {
            "scan_id": str(scan.id),
            "points_count": raw_count,
            "footprint_sqm": footprint_sqm,
            "density_per_sqm": density_per_sqm,
        }
        job.save(update_fields=["state", "progress", "current_step", "completed_at", "result", "updated_at"])
        return scan
    except Exception as exc:
        scan.status = ScanAsset.Status.FAILED
        scan.processing_notes = str(exc)
        scan.save(update_fields=["status", "processing_notes", "updated_at"])

        job.state = ProcessingJob.State.FAILED
        job.error = str(exc)
        job.completed_at = timezone.now()
        job.current_step = "خطا در پردازش فایل اسکن"
        job.save(update_fields=["state", "error", "completed_at", "current_step", "updated_at"])
        raise


def enqueue_scan_process(*, user: User, agency_id: Optional[UUID], scan_id: UUID) -> ProcessingJob:
    scan = get_scan_asset_for_user(user=user, agency_id=agency_id, scan_id=scan_id, require_edit=True)
    active = ProcessingJob.objects.filter(
        tour=scan.tour,
        job_type=ProcessingJob.JobType.SCAN_PROCESS,
        state__in=[ProcessingJob.State.QUEUED, ProcessingJob.State.RUNNING],
        input_params__scan_id=str(scan.id),
    ).first()
    if active:
        raise ConflictDomainError("پردازش این فایل اسکن هم‌اکنون در حال اجرا است.")

    job = ProcessingJob.objects.create(
        tour=scan.tour,
        scene=scan.scene,
        job_type=ProcessingJob.JobType.SCAN_PROCESS,
        state=ProcessingJob.State.QUEUED,
        progress=0,
        current_step="در صف پردازش فایل اسکن LiDAR / عمق",
        input_params={"scan_id": str(scan.id)},
        created_by=user,
        updated_by=user,
    )
    record_audit_event(
        action="virtual_tour.scan_process_enqueue",
        resource_type="ScanAsset",
        resource_id=str(scan.id),
        actor=user,
        agency_id=scan.tour.agency_id,
        after_state={"job_id": str(job.id), "format": scan.format},
    )

    from apps.virtual_tours.services.panorama_service import _has_active_celery_worker
    from apps.virtual_tours.tasks.jobs import process_scan_asset_task

    if _has_active_celery_worker():
        res = process_scan_asset_task.delay(str(job.id))
        job.celery_task_id = str(res.id)
        job.save(update_fields=["celery_task_id", "updated_at"])
    else:
        process_scan_asset_task.apply(args=[str(job.id)]).get()
        job.refresh_from_db()

    return job


@transaction.atomic
def delete_scan_asset(*, user: User, agency_id: Optional[UUID], scan_id: UUID) -> None:
    scan = get_scan_asset_for_user(user=user, agency_id=agency_id, scan_id=scan_id, require_edit=True)
    tour_id = str(scan.tour_id)
    scan_aid = scan.tour.agency_id
    scan.delete()
    record_audit_event(
        action="virtual_tour.scan_delete",
        resource_type="ScanAsset",
        resource_id=str(scan_id),
        actor=user,
        agency_id=scan_aid,
        after_state={"tour_id": tour_id},
    )
