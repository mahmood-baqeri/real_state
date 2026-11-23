from typing import Any, Optional
from uuid import UUID
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.audit.services import record_audit_event
from apps.virtual_tours.models import CaptureGuideStep, CaptureImage, CaptureSession, Scene, VirtualTour
from apps.virtual_tours.selectors import get_capture_session_for_user, get_scene_for_user
from apps.virtual_tours.services.quality_service import (
    analyze_capture_image,
    evaluate_capture_session_quality,
)
from apps.virtual_tours.services.settings_service import get_capture_policy
from apps.virtual_tours.validators import validate_capture_image_upload
from common.exceptions import ValidationDomainError
from integrations.registry import get_storage_provider


def _build_guide_steps_blueprint(policy: dict[str, Any]) -> list[dict[str, Any]]:
    h_count = policy["horizontal_steps"]
    overlap = policy["target_overlap_percent"]
    steps: list[dict[str, Any]] = []
    step_deg = 360.0 / h_count
    for i in range(h_count):
        yaw = round(i * step_deg, 1)
        steps.append({
            "sequence": len(steps) + 1,
            "yaw": yaw,
            "pitch": 0.0,
            "label": f"نمای افقی {int(yaw)}°",
            "required": True,
            "expected_overlap_percent": overlap,
            "guidance": f"دوربین را در ارتفاع چشم به سمت زاویه {int(yaw)} درجه بچرخانید و با حدود {int(overlap)}٪ همپوشانی ثبت کنید.",
        })

    # Two overlapping elevation rings prevent the large blank bands produced by
    # stitching only eye-level frames plus a single stretched ceiling/floor image.
    for pitch, label in ((40.0, "نمای بالایی"), (-40.0, "نمای پایینی")):
        for i in range(6):
            yaw = float(i * 60)
            steps.append({
                "sequence": len(steps) + 1,
                "yaw": yaw,
                "pitch": pitch,
                "label": f"{label} {int(yaw)}°",
                "required": True,
                "expected_overlap_percent": overlap,
                "guidance": f"دوربین را در جهت {int(yaw)} درجه و با شیب {int(pitch)} درجه بگیرید؛ بخشی از دیوار و سقف/کف در تصویر هم‌پوشانی داشته باشد.",
            })

    if policy["require_ceiling_floor"]:
        for pitch, label, guidance in (
            (80.0, "سقف", "دوربین را نزدیک به ۸۰ درجه به سمت بالا بگیرید."),
            (-80.0, "کف", "دوربین را نزدیک به ۸۰ درجه به سمت پایین بگیرید."),
        ):
            for yaw in (0.0, 120.0, 240.0):
                steps.append({
                    "sequence": len(steps) + 1,
                    "yaw": yaw,
                    "pitch": pitch,
                    "label": f"{label} · زاویه {int(yaw)}°",
                    "required": True,
                    "expected_overlap_percent": overlap,
                    "guidance": f"{guidance} گوشی را به جهت {int(yaw)} درجه بچرخانید تا ناحیه قطب تصویر کامل پوشش داده شود.",
                })
    return steps


@transaction.atomic
def start_capture_session(
    *,
    user: User,
    agency_id: Optional[UUID],
    scene_id: UUID,
    device_info: Optional[dict[str, Any]] = None,
    allow_partial_stitch: bool = False,
) -> CaptureSession:
    scene = get_scene_for_user(user=user, agency_id=agency_id, scene_id=scene_id, require_edit=True)
    policy = get_capture_policy(tour=scene.tour)
    session = CaptureSession.objects.create(
        tour=scene.tour,
        scene=scene,
        status=CaptureSession.Status.CAPTURING,
        device_info=device_info or {},
        capture_config={**policy, "allow_partial_stitch": bool(allow_partial_stitch)},
        started_at=timezone.now(),
        created_by=user,
        updated_by=user,
    )
    for bp in _build_guide_steps_blueprint(policy):
        CaptureGuideStep.objects.create(
            session=session,
            sequence=bp["sequence"],
            yaw=bp["yaw"],
            pitch=bp["pitch"],
            label=bp["label"],
            required=bp["required"],
            expected_overlap_percent=bp["expected_overlap_percent"],
            guidance=bp["guidance"],
            created_by=user,
        )

    if scene.tour.status in (VirtualTour.Status.DRAFT, VirtualTour.Status.FAILED):
        scene.tour.status = VirtualTour.Status.CAPTURING
        scene.tour.updated_by = user
        scene.tour.save(update_fields=["status", "updated_by", "updated_at"])

    record_audit_event(
        action="virtual_tour.capture_session_start",
        resource_type="CaptureSession",
        resource_id=str(session.id),
        actor=user,
        agency_id=scene.tour.agency_id,
        after_state={"scene_id": str(scene.id), "steps": len(session.guide_steps.all())},
    )
    return session


@transaction.atomic
def upload_capture_image(
    *,
    user: User,
    agency_id: Optional[UUID],
    session_id: UUID,
    filename: str,
    content_type: str,
    content: bytes,
    sequence: int,
    yaw: Optional[float] = None,
    pitch: Optional[float] = None,
) -> tuple[CaptureImage, dict[str, Any]]:
    session = get_capture_session_for_user(
        user=user, agency_id=agency_id, session_id=session_id, require_edit=True
    )
    if session.status == CaptureSession.Status.CANCELLED:
        raise ValidationDomainError("این جلسه عکاسی لغو شده است و امکان آپلود تصویر در آن وجود ندارد.")

    policy = get_capture_policy(tour=session.tour)
    safe_name, mime, width, height, normalized_bytes = validate_capture_image_upload(
        filename=filename,
        content_type=content_type,
        content=content,
        max_mb=policy["max_upload_file_mb"],
    )

    step = session.guide_steps.filter(sequence=sequence).first()
    eff_yaw = float(yaw) if yaw is not None else (step.yaw if step else float((sequence - 1) * 30))
    eff_pitch = float(pitch) if pitch is not None else (step.pitch if step else 0.0)

    # Collect existing perceptual hashes in session excluding current sequence (retake)
    existing_hashes: list[int] = []
    for other in session.images.exclude(sequence=sequence).exclude(status=CaptureImage.Status.REPLACED):
        h_hex = (other.analysis or {}).get("dhash")
        if isinstance(h_hex, str) and h_hex.startswith("0x"):
            try:
                existing_hashes.append(int(h_hex, 16))
            except ValueError:
                pass

    qc_status, analysis = analyze_capture_image(
        image_bytes=normalized_bytes,
        existing_hashes=existing_hashes,
        policy=policy,
    )

    storage = get_storage_provider()
    prefix = f"private/virtual_tours/{session.tour.agency_id}/{session.tour_id}/captures/{session.id}"
    stored = storage.put_bytes(
        key_prefix=prefix,
        safe_filename=f"seq-{sequence:02d}-{safe_name}",
        content=normalized_bytes,
        mime_type=mime,
    )

    img, _ = CaptureImage.objects.update_or_create(
        session=session,
        sequence=sequence,
        defaults={
            "scene": session.scene,
            "storage_key": stored.file_key,
            "filename": filename[:255],
            "mime_type": mime,
            "size_bytes": stored.size_bytes,
            "width": width,
            "height": height,
            "status": qc_status,
            "analysis": analysis,
            "yaw": eff_yaw,
            "pitch": eff_pitch,
            "captured_at": timezone.now(),
            "created_by": user,
            "updated_by": user,
        },
    )

    if step:
        step.image = img
        if qc_status == CaptureImage.Status.REJECTED:
            step.state = CaptureGuideStep.State.NEEDS_RETAKE
        elif qc_status == CaptureImage.Status.PASSED:
            step.state = CaptureGuideStep.State.PASSED
        else:
            step.state = CaptureGuideStep.State.CAPTURED
        step.updated_by = user
        step.save(update_fields=["image", "state", "updated_by", "updated_at"])

    session.status = (
        CaptureSession.Status.NEEDS_RETAKE
        if qc_status == CaptureImage.Status.REJECTED
        else CaptureSession.Status.CAPTURING
    )
    session.updated_by = user
    session.save(update_fields=["status", "updated_by", "updated_at"])

    summary = evaluate_capture_session_quality(session)
    record_audit_event(
        action="virtual_tour.capture_image_upload",
        resource_type="CaptureImage",
        resource_id=str(img.id),
        actor=user,
        agency_id=session.tour.agency_id,
        after_state={"session_id": str(session.id), "sequence": sequence, "qc_status": qc_status},
    )
    return img, summary


@transaction.atomic
def skip_capture_step(
    *,
    user: User,
    agency_id: Optional[UUID],
    session_id: UUID,
    sequence: int,
) -> CaptureGuideStep:
    session = get_capture_session_for_user(
        user=user, agency_id=agency_id, session_id=session_id, require_edit=True
    )
    step = session.guide_steps.filter(sequence=sequence).first()
    if not step:
        raise ValidationDomainError("مرحله راهنمای مورد نظر یافت نشد.")
    if step.required:
        raise ValidationDomainError("این مرحله الزامی است و قابل رد کردن نیست.")
    step.state = CaptureGuideStep.State.SKIPPED
    step.updated_by = user
    step.save(update_fields=["state", "updated_by", "updated_at"])
    return step


@transaction.atomic
def complete_capture_session(
    *,
    user: User,
    agency_id: Optional[UUID],
    session_id: UUID,
) -> tuple[CaptureSession, dict[str, Any]]:
    session = get_capture_session_for_user(
        user=user, agency_id=agency_id, session_id=session_id, require_edit=True
    )
    summary = evaluate_capture_session_quality(session)
    if summary["usable_images_count"] < 2:
        raise ValidationDomainError("برای تکمیل جلسه عکاسی حداقل ۲ تصویر قابل استفاده نیاز است.")

    if not summary["ready_to_stitch"]:
        session.status = CaptureSession.Status.NEEDS_RETAKE
        session.save(update_fields=["status", "updated_at"])
        raise ValidationDomainError(
            f"تعداد تصاویر قابل استفاده ({summary['usable_images_count']}) کمتر از حداقل لازم ({summary['min_usable_required']}) است. تصاویر ناقص یا تار را تکرار کنید."
        )

    session.status = CaptureSession.Status.READY
    session.completed_at = timezone.now()
    session.updated_by = user
    session.save(update_fields=["status", "completed_at", "updated_by", "updated_at"])
    return session, summary


@transaction.atomic
def cancel_capture_session(
    *,
    user: User,
    agency_id: Optional[UUID],
    session_id: UUID,
) -> CaptureSession:
    session = get_capture_session_for_user(
        user=user, agency_id=agency_id, session_id=session_id, require_edit=True
    )
    session.status = CaptureSession.Status.CANCELLED
    session.updated_by = user
    session.save(update_fields=["status", "updated_by", "updated_at"])
    return session
