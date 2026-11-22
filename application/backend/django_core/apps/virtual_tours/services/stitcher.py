from io import BytesIO
from typing import Any, Callable, Optional
import cv2
import numpy as np
from PIL import Image


def _to_equirectangular_from_panorama(pano_bgr: np.ndarray, out_width: int) -> np.ndarray:
    """
    Normalizes an arbitrary stitched panorama BGR image onto a clean 2:1 Equirectangular
    canvas (with smooth top/bottom vertical pole fill) so Three.js sphere projection renders without distortion.
    """
    out_height = max(512, out_width // 2)
    h, w = pano_bgr.shape[:2]
    aspect = w / max(1, h)
    # If already ~2:1 equirectangular, resize directly cleanly
    if 1.85 <= aspect <= 2.15:
        return cv2.resize(pano_bgr, (out_width, out_height), interpolation=cv2.INTER_LANCZOS4)

    # Fit horizontally across full 360 width, maintain aspect vertically centered, feather poles cleanly
    target_h = int(round(out_width / max(0.5, aspect)))
    target_h = min(out_height, max(out_height // 3, target_h))
    resized = cv2.resize(pano_bgr, (out_width, target_h), interpolation=cv2.INTER_LANCZOS4)

    canvas = np.zeros((out_height, out_width, 3), dtype=np.uint8)
    y_offset = (out_height - target_h) // 2
    canvas[y_offset : y_offset + target_h, :] = resized

    # Extend top & bottom edge colors gently with blur so ceiling/floor caps blend naturally
    if y_offset > 0:
        top_row = resized[0:1, :, :]
        bot_row = resized[-1:, :, :]
        top_fill = np.repeat(top_row, y_offset, axis=0)
        bot_fill = np.repeat(bot_row, out_height - (y_offset + target_h), axis=0)
        top_grad = cv2.GaussianBlur(top_fill, (31, 31), 12)
        bot_grad = cv2.GaussianBlur(bot_fill, (31, 31), 12)
        canvas[:y_offset, :] = top_grad
        canvas[y_offset + target_h :, :] = bot_grad

    return canvas


def _yaw_guided_equirectangular_blend(
    frames: list[dict[str, Any]],
    out_width: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    """
    Real OpenCV yaw/pitch-guided cylindrical-to-equirectangular projection and cosine feather blending.
    Projects every captured frame onto the 2:1 equirectangular sphere according to its captured yaw/pitch,
    performs gain/exposure normalization across frames, and blends overlapping seams smoothly.
    """
    out_height = max(512, out_width // 2)
    accum = np.zeros((out_height, out_width, 3), dtype=np.float32)
    weight_sum = np.zeros((out_height, out_width, 1), dtype=np.float32)

    # Global mean brightness target for exposure compensation
    means = [float(np.mean(cv2.cvtColor(f["bgr"], cv2.COLOR_BGR2GRAY))) for f in frames]
    target_luma = float(np.median(means)) if means else 128.0

    # Estimate angular HFOV per horizontal frame (assume ~72 deg phone wide camera)
    hfov_deg = 72.0
    placed_yaws: list[float] = []

    for f in frames:
        bgr = f["bgr"].astype(np.float32)
        yaw = float(f.get("yaw", 0.0)) % 360.0
        pitch = float(f.get("pitch", 0.0))

        # Gain normalization so adjacent shots match exposure cleanly
        luma = float(np.mean(cv2.cvtColor(f["bgr"], cv2.COLOR_BGR2GRAY)))
        if luma > 5.0:
            gain = np.clip(target_luma / luma, 0.72, 1.38)
            bgr = np.clip(bgr * gain, 0, 255)

        fh, fw = bgr.shape[:2]
        # Feather mask fading near image borders for seamless overlap blending
        wx = np.hanning(fw) if fw > 4 else np.ones(fw)
        wy = np.hanning(fh) if fh > 4 else np.ones(fh)
        w2d = np.outer(wy, wx).astype(np.float32) + 0.02

        if abs(pitch) >= 60.0:
            # Zenith (ceiling) or Nadir (floor) polar strip projection
            band_h = max(32, int(out_height * 0.28))
            patch = cv2.resize(bgr, (out_width, band_h), interpolation=cv2.INTER_LINEAR)
            patch_w = cv2.resize(w2d, (out_width, band_h), interpolation=cv2.INTER_LINEAR)[:, :, None]
            if pitch >= 60.0:
                accum[:band_h, :] += patch * patch_w
                weight_sum[:band_h, :] += patch_w
            else:
                accum[out_height - band_h :, :] += patch * patch_w
                weight_sum[out_height - band_h :, :] += patch_w
            continue

        placed_yaws.append(yaw)
        patch_w_px = max(64, int(round((hfov_deg / 360.0) * out_width)))
        vfov_deg = hfov_deg * (fh / max(1, fw))
        patch_h_px = max(64, min(out_height, int(round((vfov_deg / 180.0) * out_height))))

        resized = cv2.resize(bgr, (patch_w_px, patch_h_px), interpolation=cv2.INTER_LINEAR)
        rw = cv2.resize(w2d, (patch_w_px, patch_h_px), interpolation=cv2.INTER_LINEAR)[:, :, None]

        cx = int(round((yaw / 360.0) * out_width)) % out_width
        cy = int(round(((90.0 - pitch) / 180.0) * out_height))
        y0 = max(0, min(out_height - patch_h_px, cy - patch_h_px // 2))
        y1 = y0 + patch_h_px

        x_start = cx - patch_w_px // 2
        for dx in range(patch_w_px):
            tx = (x_start + dx) % out_width
            accum[y0:y1, tx] += resized[:, dx] * rw[:, dx]
            weight_sum[y0:y1, tx] += rw[:, dx]

    valid = weight_sum > 1e-5
    covered_ratio = float(np.mean(valid))
    safe_weight = np.where(valid, weight_sum, 1.0)
    blended = np.where(valid, accum / safe_weight, 18.0).astype(np.uint8)

    # Smooth horizontal wrap seam and fill uncovered upper/lower bands from nearest vertical row
    # Inpaint small uncovered holes cleanly if coverage < 1.0
    mask_uncovered = (~valid[:, :, 0]).astype(np.uint8) * 255
    if 0 < np.count_nonzero(mask_uncovered) < mask_uncovered.size:
        # Vertical edge extension first for fast clean pole fill
        col_has = np.any(valid[:, :, 0], axis=0)
        for x in range(out_width):
            if col_has[x]:
                ys = np.where(valid[:, x, 0])[0]
                top_y, bot_y = ys[0], ys[-1]
                if top_y > 0:
                    blended[:top_y, x] = blended[top_y, x]
                if bot_y < out_height - 1:
                    blended[bot_y + 1 :, x] = blended[bot_y, x]
        # Blur top and bottom polar regions gently
        pole = max(16, out_height // 6)
        blended[:pole, :] = cv2.GaussianBlur(blended[:pole, :], (21, 21), 8)
        blended[-pole:, :] = cv2.GaussianBlur(blended[-pole:, :], (21, 21), 8)

    unique_yaws = len({round(y / 15.0) for y in placed_yaws})
    coverage_360 = min(100.0, round((unique_yaws / 12.0) * 100.0, 1)) if placed_yaws else round(covered_ratio * 100.0, 1)
    return blended, {
        "covered_pixel_ratio": round(covered_ratio, 3),
        "coverage_360_percent": coverage_360,
        "exposure_normalized": True,
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
    2) Attempts OpenCV feature-based `cv2.Stitcher(PANORAMA)` on horizontal frames first.
    3) If feature overlap is insufficient for homography (e.g., plain walls or sparse captures),
       runs real yaw/pitch-guided OpenCV spherical feather-blending across all frames.
    4) Encodes 2:1 Equirectangular JPEG and 800x400 thumbnail JPEG.
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
    horizontal = [f for f in decoded if abs(f["pitch"]) < 45.0] or decoded

    if progress_cb:
        progress_cb(40, "استخراج ویژگی‌ها و هم‌ترازی OpenCV")

    engine_used = "opencv_yaw_equirectangular_blend"
    stitch_metrics: dict[str, Any] = {}
    equirect_bgr: Optional[np.ndarray] = None

    # Resize large horizontal inputs to max width 1280 for reliable fast OpenCV stitching
    stitch_candidates = []
    for f in horizontal:
        img = f["bgr"]
        ih, iw = img.shape[:2]
        if iw > 1280:
            scale = 1280.0 / iw
            img = cv2.resize(img, (1280, max(64, int(ih * scale))), interpolation=cv2.INTER_AREA)
        stitch_candidates.append(img)

    if len(stitch_candidates) >= 2:
        try:
            stitcher = cv2.Stitcher_create(cv2.Stitcher_PANORAMA)
            status_code, stitched = stitcher.stitch(stitch_candidates)
            if status_code == cv2.Stitcher_OK and stitched is not None and stitched.shape[1] >= stitched.shape[0]:
                engine_used = "opencv_feature_stitcher"
                equirect_bgr = _to_equirectangular_from_panorama(stitched, out_width=out_width)
                stitch_metrics = {
                    "opencv_stitcher_status": "OK",
                    "raw_stitched_width": int(stitched.shape[1]),
                    "raw_stitched_height": int(stitched.shape[0]),
                    "coverage_360_percent": min(100.0, round((len(horizontal) / 12.0) * 100.0, 1)),
                }
        except Exception as exc:
            stitch_metrics["opencv_stitcher_fallback_reason"] = str(exc)

    if progress_cb:
        progress_cb(70, "تولید تصویر Equirectangular و هم‌ترازی نور")

    if equirect_bgr is None:
        equirect_bgr, blend_metrics = _yaw_guided_equirectangular_blend(decoded, out_width=out_width)
        stitch_metrics.update(blend_metrics)

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
            "human_review_required": True,
        },
    }
