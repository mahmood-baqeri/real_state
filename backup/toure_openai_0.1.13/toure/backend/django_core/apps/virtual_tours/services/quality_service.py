import cv2
import numpy as np
from typing import Any
from apps.virtual_tours.models import (
    CaptureImage,
    CaptureSession,
    PanoramaVersion,
    ProcessingJob,
    SceneLink,
    TourQualityReport,
    VirtualTour,
)
from apps.virtual_tours.policies.access import is_property_publicly_publishable
from apps.virtual_tours.services.settings_service import get_capture_policy, get_tour_limits


def _compute_dhash(gray: np.ndarray, hash_size: int = 8) -> int:
    resized = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    diff = resized[:, 1:] > resized[:, :-1]
    val = 0
    for idx, bit in enumerate(diff.flatten()):
        if bit:
            val |= 1 << idx
    return val


def _hamming_distance(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def analyze_capture_image(
    *,
    image_bytes: bytes,
    existing_hashes: list[int],
    policy: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """
    Runs real OpenCV quality inspection on an uploaded capture frame:
    - Corrupt / unreadable image check
    - Resolution check against configured minimums
    - Blur check via variance of Laplacian
    - Under-exposure / over-exposure brightness check
    - Contrast (stddev of luminance) & noise estimate
    - Perceptual dHash duplicate check against existing session images
    """
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        return CaptureImage.Status.REJECTED, {
            "corrupt": True,
            "issues": ["تصویر قابل رمزگشایی نیست یا ساختار آن خراب است."],
            "recommendations": ["لطفاً مجدداً با دوربین عکس بگیرید."],
        }

    height, width = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))

    # Estimate sensor noise via residual between image and median-filtered version
    median = cv2.medianBlur(gray, 3)
    noise_level = float(np.mean(np.abs(gray.astype(np.float32) - median.astype(np.float32))))

    dhash = _compute_dhash(gray)
    min_hamming = min((_hamming_distance(dhash, h) for h in existing_hashes), default=64)
    is_duplicate = min_hamming <= 3

    issues: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []

    if width < policy["min_image_width_px"] or height < policy["min_image_height_px"]:
        warnings.append(
            f"رزولوشن تصویر ({width}×{height}) کمتر از حداقل توصیه‌شده ({policy['min_image_width_px']}×{policy['min_image_height_px']}) است."
        )
        recommendations.append("کیفیت دوربین را روی حالت استاندارد یا HD قرار دهید.")

    if blur_score < policy["min_blur_score"]:
        issues.append(f"تاری و لرزش تصویر بالا است (شاخص وضوح: {blur_score:.1f}).")
        recommendations.append("هنگام عکاسی گوشی را ثابت نگه دارید و یک ثانیه مکث کنید.")

    if brightness < policy["min_brightness"]:
        issues.append(f"نور تصویر بسیار کم و تاریک است (روشنایی: {brightness:.1f}).")
        recommendations.append("چراغ‌های فضا را روشن کنید یا نور محیط را افزایش دهید.")
    elif brightness > policy["max_brightness"]:
        issues.append(f"نور بیش از حد (Overexposed) است (روشنایی: {brightness:.1f}).")
        recommendations.append("از روبه‌رو گرفتن مستقیم دوربین به پنجره یا لامپ پرنور خودداری کنید.")

    if contrast < policy["min_contrast"]:
        warnings.append(f"کنتراست تصویر پایین است ({contrast:.1f})؛ ممکن است دوخت دقیق ویژگی کمتری داشته باشد.")
        recommendations.append("زاویه دوربین را طوری تنظیم کنید که جزئیات معماری در کادر دیده شود.")

    if is_duplicate:
        warnings.append("این تصویر شباهت بسیار زیادی به یکی از فریم‌های قبلی دارد (تکراری احتمالی).")
        recommendations.append("مطابق راهنما حداقل ۳۰ درجه بچرخید و دوباره عکس بگیرید.")

    if issues:
        status = CaptureImage.Status.REJECTED
    elif warnings:
        status = CaptureImage.Status.WARNING
    else:
        status = CaptureImage.Status.PASSED

    return status, {
        "corrupt": False,
        "width": int(width),
        "height": int(height),
        "blur_score": round(blur_score, 2),
        "brightness": round(brightness, 2),
        "contrast": round(contrast, 2),
        "noise_level": round(noise_level, 2),
        "dhash": hex(dhash),
        "min_hamming_distance": int(min_hamming),
        "is_duplicate": bool(is_duplicate),
        "issues": issues,
        "warnings": warnings,
        "recommendations": recommendations,
    }


def evaluate_capture_session_quality(session: CaptureSession) -> dict[str, Any]:
    steps = list(session.guide_steps.order_by("sequence"))
    images = list(session.images.exclude(status=CaptureImage.Status.REPLACED).order_by("sequence"))
    policy = get_capture_policy(tour=session.tour)

    total_steps = len(steps)
    captured_steps = sum(1 for s in steps if s.state in ("captured", "passed"))
    skipped_steps = sum(1 for s in steps if s.state == "skipped")
    retake_steps = sum(1 for s in steps if s.state == "needs_retake")
    rejected_count = sum(1 for img in images if img.status == CaptureImage.Status.REJECTED)
    usable_count = sum(1 for img in images if img.status in (CaptureImage.Status.PASSED, CaptureImage.Status.WARNING, CaptureImage.Status.UPLOADED))

    horizontal_yaws = sorted(
        {
            round(img.yaw % 360.0, 1)
            for img in images
            if img.status != CaptureImage.Status.REJECTED and abs(img.pitch) < 20
        }
    )
    has_ceiling = any(img.pitch >= 45 and img.status != CaptureImage.Status.REJECTED for img in images)
    has_floor = any(img.pitch <= -45 and img.status != CaptureImage.Status.REJECTED for img in images)

    gaps: list[str] = []
    if len(horizontal_yaws) >= 2:
        for i in range(len(horizontal_yaws)):
            nxt = horizontal_yaws[(i + 1) % len(horizontal_yaws)]
            diff = (nxt - horizontal_yaws[i]) % 360.0
            if diff > 65:
                gaps.append(f"شکاف زاویه‌ای {diff:.0f}° بین {horizontal_yaws[i]:.0f}° و {nxt:.0f}°")

    return {
        "session_id": str(session.id),
        "total_steps": total_steps,
        "captured_steps": captured_steps,
        "skipped_steps": skipped_steps,
        "retake_steps": retake_steps,
        "usable_images_count": usable_count,
        "rejected_images_count": rejected_count,
        "min_usable_required": policy["min_usable_images_for_stitch"],
        "ready_to_stitch": usable_count >= policy["min_usable_images_for_stitch"] or len(images) >= 2 and bool(session.capture_config.get("allow_partial_stitch")),
        "has_ceiling": has_ceiling,
        "has_floor": has_floor,
        "angular_gaps": gaps,
        "completion_percent": round((captured_steps / max(1, total_steps)) * 100, 1),
    }


def generate_tour_quality_report(tour: VirtualTour, actor=None) -> TourQualityReport:
    limits = get_tour_limits(tour=tour)
    floors = list(tour.floors.order_by("order"))
    scenes = list(tour.scenes.filter(active=True).order_by("floor__order", "order"))
    links = list(tour.links.all())
    failed_jobs = ProcessingJob.objects.filter(tour=tour, state=ProcessingJob.State.FAILED).count()

    blocking_issues: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if tour.status == VirtualTour.Status.ARCHIVED:
        blocking_issues.append({
            "code": "TOUR_ARCHIVED",
            "message": "این تور آرشیو شده و قابل انتشار نیست.",
            "fix": "برای انتشار، تور جدید ایجاد کنید یا وضعیت را بازگردانی کنید.",
        })

    if not floors:
        blocking_issues.append({
            "code": "NO_FLOORS",
            "message": "حداقل یک طبقه باید برای تور تعریف شده باشد.",
            "fix": "در بخش مدیریت طبقات، طبقه اول را ایجاد کنید.",
        })

    if not scenes:
        blocking_issues.append({
            "code": "NO_SCENES",
            "message": "هیچ اتاق فعالی در تور ثبت نشده است.",
            "fix": "حداقل یک اتاق یا فضا را به طبقه اضافه کنید.",
        })

    start_scenes = [s for s in scenes if s.is_start_scene]
    if scenes and not start_scenes:
        blocking_issues.append({
            "code": "NO_START_SCENE",
            "message": "اتاق شروع (Start Scene) مشخص نشده است.",
            "fix": "در فهرست اتاق‌ها، یکی از فضاها (ترجیحاً پذیرایی یا ورودی) را به‌عنوان نقطه شروع انتخاب کنید.",
        })

    approved_panoramas_count = 0
    captured_scenes_count = 0
    incomplete_scenes: list[dict[str, str]] = []
    rejected_images_total = CaptureImage.objects.filter(
        scene__tour=tour, status=CaptureImage.Status.REJECTED
    ).count()

    for sc in scenes:
        has_capture = sc.capture_images.exclude(status=CaptureImage.Status.REJECTED).exists()
        if has_capture:
            captured_scenes_count += 1
        current_pano = sc.panorama_versions.filter(is_current=True).first()
        if not current_pano:
            incomplete_scenes.append({
                "scene_id": str(sc.id),
                "title": sc.title,
                "reason": "فاقد پانورامای پردازش‌شده",
            })
            blocking_issues.append({
                "code": "SCENE_MISSING_PANORAMA",
                "message": f"اتاق «{sc.title}» هنوز پانوراما ندارد.",
                "fix": f"برای اتاق «{sc.title}» عکاسی یا آپلود انجام دهید و پردازش را اجرا کنید.",
            })
        elif (current_pano.quality_report or {}).get("coverage_complete") is False:
            coverage_warning = (current_pano.quality_report or {}).get("coverage_warning") or "پوشش تصویری پانوراما کامل نیست."
            incomplete_scenes.append({
                "scene_id": str(sc.id),
                "title": sc.title,
                "reason": "پوشش تصویری ناقص",
            })
            blocking_issues.append({
                "code": "PANORAMA_COVERAGE_INCOMPLETE",
                "message": f"پانورامای اتاق «{sc.title}» بخش‌های بدون تصویر دارد.",
                "fix": str(coverage_warning),
            })
        elif current_pano.state != PanoramaVersion.State.APPROVED:
            if limits["require_manager_approval"] or current_pano.state != PanoramaVersion.State.REVIEW:
                incomplete_scenes.append({
                    "scene_id": str(sc.id),
                    "title": sc.title,
                    "reason": f"وضعیت پانوراما: {current_pano.state}",
                })
                blocking_issues.append({
                    "code": "PANORAMA_NOT_APPROVED",
                    "message": f"پانورامای فعلی اتاق «{sc.title}» هنوز تأیید نهایی نشده است.",
                    "fix": f"در نمای بازبینی پانورامای «{sc.title}»، نسخه را تأیید کنید.",
                })
            else:
                approved_panoramas_count += 1
        else:
            approved_panoramas_count += 1

    if len(scenes) > 1 and not links:
        warnings.append({
            "code": "NO_SCENE_LINKS",
            "message": "بین اتاق‌های تور هنوز لینک ناوبری (SceneLink) تعریف نشده است.",
            "fix": "در ویرایشگر پانوراما نقاط انتقال بین اتاق‌ها را ثبت کنید تا بازدیدکننده بتواند بین فضاها جابه‌جا شود.",
        })

    for lnk in links:
        if lnk.source_scene.tour_id != tour.id or lnk.target_scene.tour_id != tour.id:
            blocking_issues.append({
                "code": "INVALID_LINK",
                "message": "یک لینک ناوبری به اتاق نامعتبر متصل است.",
                "fix": "لینک نامعتبر را حذف و مجدداً ایجاد کنید.",
            })

    if not is_property_publicly_publishable(tour.property):
        warnings.append({
            "code": "PROPERTY_NOT_PUBLIC_PORTAL",
            "message": "خود ملک هنوز در پورتال عمومی منتشر نشده است (وضعیت PUBLISHED و PUBLIC_PORTAL نیست).",
            "fix": "پس از آماده‌سازی تور، ملک را از صفحه مدیریت ملک در پورتال عمومی منتشر کنید تا بازدید مجازی به خریداران نمایش داده شود.",
        })

    if failed_jobs > 0:
        warnings.append({
            "code": "FAILED_JOBS_EXIST",
            "message": f"{failed_jobs} پردازش ناموفق در تاریخچه تور ثبت شده است.",
            "fix": "در بخش پردازش‌ها (Jobs) جزئیات خطا را بررسی یا مجدداً اجرا کنید.",
        })

    active_plans = list(tour.floorplans.filter(is_active=True))
    calibrated_plans = [p for p in active_plans if p.scale_m_per_px is not None]
    rooms_count = tour.room_geometries.count()
    walls_count = tour.wall_segments.count()
    current_model = tour.generated_models.filter(is_current=True).first() or tour.generated_models.order_by("-version").first()
    scans_qs = list(tour.scans.all())
    validated_scans = [s for s in scans_qs if s.status == "validated"]

    geometry_issues: list[str] = []
    if active_plans and not calibrated_plans:
        geometry_issues.append("پلان دو‌بعدی آپلود شده هنوز با دو نقطه کالیبره نشده است.")
    if rooms_count > 0 and not current_model:
        geometry_issues.append("اتاق‌های پلان تعریف شده‌اند اما هنوز مدل سه‌بعدی Dollhouse تولید نشده است.")

    is_ready = len(blocking_issues) == 0
    report_data = {
        "floors_count": len(floors),
        "scenes_count": len(scenes),
        "captured_scenes_count": captured_scenes_count,
        "approved_panoramas_count": approved_panoramas_count,
        "incomplete_scenes": incomplete_scenes,
        "rejected_images_count": rejected_images_total,
        "failed_jobs_count": failed_jobs,
        "links_count": len(links),
        "plan_status": {
            "uploaded_count": len(active_plans),
            "calibrated_count": len(calibrated_plans),
            "rooms_count": rooms_count,
            "walls_count": walls_count,
        },
        "dollhouse_status": {
            "has_model": current_model is not None,
            "current_version": current_model.version if current_model else None,
            "state": current_model.state if current_model else "not_built",
            "geometry_source": current_model.geometry_source if current_model else "none",
            "estimated_accuracy": current_model.estimated_accuracy if current_model else "",
        },
        "scan_status": {
            "total_count": len(scans_qs),
            "validated_count": len(validated_scans),
            "total_points": sum(int(s.points_count or 0) for s in validated_scans),
        },
        "geometry_issues": geometry_issues,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "ready_for_publish": is_ready,
    }
    return TourQualityReport.objects.create(
        tour=tour,
        report_data=report_data,
        is_ready_to_publish=is_ready,
        blocking_issues_count=len(blocking_issues),
        warning_issues_count=len(warnings),
        created_by=actor,
    )
