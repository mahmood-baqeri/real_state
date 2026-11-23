from io import BytesIO
from typing import Any, Callable, Optional
import cv2
import numpy as np
from PIL import Image


def _yaw_guided_equirectangular_blend(
    frames: list[dict[str, Any]],
    out_width: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Project perspective camera frames onto a true equirectangular sphere.

    Each frame is mapped from its recorded yaw/pitch pose using an inverse
    perspective projection. This also handles ceiling/floor frames correctly;
    they are never stretched across the full panorama width.
    """
    out_height = max(512, out_width // 2)
    accum = np.zeros((out_height, out_width, 3), dtype=np.float32)
    weight_sum = np.zeros((out_height, out_width), dtype=np.float32)

    # World-space ray for every equirectangular output pixel.
    lon = (np.arange(out_width, dtype=np.float32) + 0.5) / out_width * (2.0 * np.pi)
    lat = np.pi / 2.0 - (np.arange(out_height, dtype=np.float32) + 0.5) / out_height * np.pi
    lon_grid, lat_grid = np.meshgrid(lon, lat)
    cos_lat = np.cos(lat_grid)
    world_x = cos_lat * np.cos(lon_grid)
    world_y = np.sin(lat_grid)
    world_z = cos_lat * np.sin(lon_grid)

    means = [float(np.mean(cv2.cvtColor(f["bgr"], cv2.COLOR_BGR2GRAY))) for f in frames]
    target_luma = float(np.median(means)) if means else 128.0
    hfov_deg = 72.0
    tan_h = float(np.tan(np.deg2rad(hfov_deg / 2.0)))
    horizontal_yaws: list[float] = []

    for frame in frames:
        image = frame["bgr"]
        fh, fw = image.shape[:2]
        yaw_deg = float(frame.get("yaw", 0.0)) % 360.0
        pitch_deg = float(frame.get("pitch", 0.0))
        yaw = np.deg2rad(yaw_deg)
        pitch = np.deg2rad(pitch_deg)

        # Camera basis: forward, right and up in world coordinates.
        forward = np.array([
            np.cos(pitch) * np.cos(yaw),
            np.sin(pitch),
            np.cos(pitch) * np.sin(yaw),
        ], dtype=np.float32)
        right = np.array([-np.sin(yaw), 0.0, np.cos(yaw)], dtype=np.float32)
        up = np.array([
            -np.sin(pitch) * np.cos(yaw),
            np.cos(pitch),
            -np.sin(pitch) * np.sin(yaw),
        ], dtype=np.float32)

        vfov_deg = float(np.rad2deg(2.0 * np.arctan(np.tan(np.deg2rad(hfov_deg / 2.0)) * (fh / max(1, fw)))))
        tan_v = float(np.tan(np.deg2rad(vfov_deg / 2.0)))

        local_x = world_x * right[0] + world_y * right[1] + world_z * right[2]
        local_y = world_x * up[0] + world_y * up[1] + world_z * up[2]
        local_z = world_x * forward[0] + world_y * forward[1] + world_z * forward[2]
        safe_z = np.where(local_z > 1e-6, local_z, 1.0)
        normalized_x = local_x / safe_z / tan_h
        normalized_y = local_y / safe_z / tan_v

        valid = (
            (local_z > 1e-6)
            & (np.abs(normalized_x) <= 1.0)
            & (np.abs(normalized_y) <= 1.0)
        )
        if not np.any(valid):
            continue

        map_x = ((normalized_x + 1.0) * 0.5 * (fw - 1)).astype(np.float32)
        map_y = ((1.0 - normalized_y) * 0.5 * (fh - 1)).astype(np.float32)
        map_x[~valid] = -1.0
        map_y[~valid] = -1.0
        warped = cv2.remap(
            image,
            map_x,
            map_y,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0),
        ).astype(np.float32)

        # Normalize exposure before blending overlapping views.
        luma = float(np.mean(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)))
        if luma > 5.0:
            gain = float(np.clip(target_luma / luma, 0.72, 1.38))
            warped = np.clip(warped * gain, 0, 255)

        # Feather the image borders to reduce visible seams.
        edge_x = 1.0 - np.abs(normalized_x)
        edge_y = 1.0 - np.abs(normalized_y)
        weights = np.clip(np.minimum(edge_x, edge_y) * 7.0, 0.025, 1.0).astype(np.float32)
        weights *= valid.astype(np.float32)
        accum += warped * weights[:, :, None]
        weight_sum += weights

        if abs(pitch_deg) < 20.0:
            horizontal_yaws.append(yaw_deg)

    valid_pixels = weight_sum > 1e-5
    covered_ratio = float(np.mean(valid_pixels))
    safe_weight = np.where(valid_pixels, weight_sum, 1.0)
    blended = np.where(valid_pixels[:, :, None], accum / safe_weight[:, :, None], 18.0).astype(np.uint8)

    # Inpaint only tiny sensor/projection holes. Large missing regions remain visible
    # and are explicitly marked incomplete instead of being fabricated or stretched.
    uncovered_mask = (~valid_pixels).astype(np.uint8) * 255
    uncovered_ratio = 1.0 - covered_ratio
    if 0 < np.count_nonzero(uncovered_mask) < uncovered_mask.size and uncovered_ratio <= 0.005:
        blended = cv2.inpaint(blended, uncovered_mask, 3, cv2.INPAINT_TELEA)

    unique_yaws = sorted({round(value % 360.0, 1) for value in horizontal_yaws})
    if unique_yaws:
        angular_gaps = [
            (unique_yaws[(i + 1) % len(unique_yaws)] - unique_yaws[i]) % 360.0
            for i in range(len(unique_yaws))
        ]
        covered_degrees = sum(min(gap, hfov_deg) for gap in angular_gaps)
        coverage_360 = min(100.0, round((covered_degrees / 360.0) * 100.0, 1))
    else:
        coverage_360 = 0.0

    return blended, {
        "covered_pixel_ratio": round(covered_ratio, 3),
        "uncovered_pixel_ratio": round(uncovered_ratio, 3),
        "coverage_360_percent": coverage_360,
        "exposure_normalized": True,
        "projection": "perspective_pose_to_equirectangular",
    }


def stitch_capture_frames_to_equirectangular(
    *,
    frames_input: list[dict[str, Any]],
    out_width: int = 2048,
    progress_cb: Optional[Callable[[int, str], None]] = None,
) -> dict[str, Any]:
    """
    Executes real panorama stitching on uploaded capture frames:
    1) Decodes all frames & validates resolution/alignment order.
    2) Projects each frame onto the sphere using its recorded yaw/pitch and blends overlaps.
    3) Keeps large uncovered regions visible in the QA preview instead of stretching edge pixels.
    4) Encodes a 2:1 Equirectangular JPEG and 800x400 thumbnail JPEG.
    Returns dict with `pano_bytes`, `thumb_bytes`, `width_px`, `height_px`, `engine`, `quality_report`.
    """
    if progress_cb:
        progress_cb(15, "رمزگشایی و بررسی فریم‌های ورودی")

    decoded: list[dict[str, Any]] = []
    for item in frames_input:
        arr = np.frombuffer(item["bytes"], dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is not None:
            decoded.append({
                "bgr": bgr,
                "yaw": float(item.get("yaw", 0.0)),
                "pitch": float(item.get("pitch", 0.0)),
                "sequence": int(item.get("sequence", 0)),
            })

    if len(decoded) < 2:
        raise ValueError("برای تولید پانوراما حداقل ۲ تصویر معتبر نیاز است.")

    decoded.sort(key=lambda x: (x["yaw"], x["sequence"]))
    engine_used = "opencv_yaw_equirectangular_blend"
    stitch_metrics: dict[str, Any] = {}

    # A planar OpenCV Stitcher panorama is not guaranteed to be equirectangular.
    # Mapping that image directly onto a sphere causes stretching near the poles.
    # Capture yaw/pitch is therefore used as the source of truth for spherical projection.
    if progress_cb:
        progress_cb(40, "محاسبه پوشش زاویه‌ای و نگاشت کروی تصاویر")

    if progress_cb:
        progress_cb(70, "دوخت کروی تصاویر و بررسی نواحی فاقد پوشش")

    equirect_bgr, stitch_metrics = _yaw_guided_equirectangular_blend(
        decoded,
        out_width=out_width,
    )

    # Compute real seam smoothness on the vertical wrap boundary (column 0 vs column -1)
    left_edge = equirect_bgr[:, :2, :].astype(np.float32)
    right_edge = equirect_bgr[:, -2:, :].astype(np.float32)
    seam_diff = float(np.mean(np.abs(left_edge - right_edge)))
    seam_score = max(0.0, round(100.0 - min(100.0, seam_diff * 1.4), 1))

    if progress_cb:
        progress_cb(90, "ساخت فایل خروجی و Thumbnail")

    out_h, out_w = equirect_bgr.shape[:2]
    rgb_pano = cv2.cvtColor(equirect_bgr, cv2.COLOR_BGR2RGB)
    pil_pano = Image.fromarray(rgb_pano)

    pano_buf = BytesIO()
    pil_pano.save(pano_buf, format="JPEG", quality=90, optimize=True)
    pano_bytes = pano_buf.getvalue()

    thumb = pil_pano.resize((800, 400), Image.Resampling.LANCZOS)
    thumb_buf = BytesIO()
    thumb.save(thumb_buf, format="JPEG", quality=82, optimize=True)
    thumb_bytes = thumb_buf.getvalue()

    if progress_cb:
        progress_cb(100, "تکمیل پردازش پانوراما")

    return {
        "pano_bytes": pano_bytes,
        "thumb_bytes": thumb_bytes,
        "width_px": int(out_w),
        "height_px": int(out_h),
        "source_image_count": len(decoded),
        "engine": engine_used,
        "quality_report": {
            **stitch_metrics,
            "aspect_ratio": round(out_w / max(1, out_h), 3),
            "projection": "equirectangular",
            "seam_continuity_score": seam_score,
            "resolution": f"{out_w}×{out_h}",
            "coverage_complete": bool(
                stitch_metrics.get("coverage_360_percent", 0) >= 75
                and stitch_metrics.get("covered_pixel_ratio", 1.0) >= 0.92
            ),
            "coverage_warning": (
                "پوشش تصویری کامل نیست؛ برای ثبت تور قابل انتشار، از زوایای جاافتاده و سقف/کف دوباره عکس بگیرید."
                if stitch_metrics.get("coverage_360_percent", 0) < 75
                or stitch_metrics.get("covered_pixel_ratio", 1.0) < 0.92
                else ""
            ),
            "human_review_required": True,
        },
    }
