from typing import Any, Optional
from uuid import UUID
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.audit.services import record_audit_event
from apps.virtual_tours.models import (
    CaptureImage,
    CaptureSession,
    PanoramaVersion,
    ProcessingJob,
    Scene,
    VirtualTour,
)
from apps.virtual_tours.policies.access import assert_tour_approve_access
from apps.virtual_tours.selectors import get_processing_job_for_user, get_scene_for_user
from apps.virtual_tours.services.settings_service import get_capture_policy, get_tour_limits
from apps.virtual_tours.services.stitcher import stitch_capture_frames_to_equirectangular
from apps.virtual_tours.validators import validate_capture_image_upload
from common.exceptions import ConflictDomainError, ValidationDomainError
from integrations.registry import get_storage_provider


def _has_active_celery_worker() -> bool:
    import os
    import sys
    from django.conf import settings

    if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    db_name = str(settings.DATABASES.get("default", {}).get("NAME", ""))
    if db_name.startswith("test_"):
        return False
    try:
        from config.celery import app as celery_app

        replies = celery_app.control.inspect(timeout=0.3).ping()
        return bool(replies)
    except Exception:
        return False


def execute_panorama_stitch_job(*, job_id: UUID) -> PanoramaVersion:
    job = ProcessingJob.objects.select_related("tour", "scene").get(id=job_id)
    if job.state == ProcessingJob.State.CANCELLED:
        raise ValidationDomainError("این پردازش لغو شده است.")

    job.state = ProcessingJob.State.RUNNING
    job.started_at = timezone.now()
    job.progress = 5
    job.current_step = "آماده‌سازی فریم‌های عکاسی"
    job.save(update_fields=["state", "started_at", "progress", "current_step", "updated_at"])

    scene = job.scene
    if not scene:
        job.state = ProcessingJob.State.FAILED
        job.error = "شناسه اتاق در Job مشخص نشده است."
        job.completed_at = timezone.now()
        job.save()
        raise ValidationDomainError(job.error)

    session_id = (job.input_params or {}).get("session_id")
    if session_id:
        session = CaptureSession.objects.filter(id=session_id, scene=scene).first()
    else:
        session = (
            scene.capture_sessions.exclude(status=CaptureSession.Status.CANCELLED)
            .order_by("-created_at")
            .first()
        )
    if not session:
        job.state = ProcessingJob.State.FAILED
        job.error = "جلسه عکاسی معتبری برای این اتاق یافت نشد."
        job.completed_at = timezone.now()
        job.save()
        raise ValidationDomainError(job.error)

    usable_images = list(
        session.images.filter(
            status__in=[CaptureImage.Status.PASSED, CaptureImage.Status.WARNING, CaptureImage.Status.UPLOADED]
        ).order_by("sequence")
    )
    if len(usable_images) < 2:
        job.state = ProcessingJob.State.FAILED
        job.error = "حداقل ۲ تصویر باکیفیت برای دوخت پانوراما لازم است."
        job.completed_at = timezone.now()
        job.save()
        raise ValidationDomainError(job.error)

    storage = get_storage_provider()
    frames_input = []
    for img in usable_images:
        raw = storage.get_bytes(file_key=img.storage_key)
        frames_input.append({
            "bytes": raw,
            "yaw": img.yaw,
            "pitch": img.pitch,
            "sequence": img.sequence,
        })

    def _on_progress(pct: int, step_msg: str) -> None:
        ProcessingJob.objects.filter(id=job.id).update(progress=pct, current_step=step_msg)

    policy = get_capture_policy(tour=scene.tour)

    try:
        stitched = stitch_capture_frames_to_equirectangular(
            frames_input=frames_input,
            out_width=policy["panorama_output_width"],
            progress_cb=_on_progress,
        )

        next_ver = (scene.panorama_versions.order_by("-version").values_list("version", flat=True).first() or 0) + 1
        prefix = f"private/virtual_tours/{scene.tour.agency_id}/{scene.tour_id}/panoramas/{scene.id}/v{next_ver}"
        pano_stored = storage.put_bytes(
            key_prefix=prefix,
            safe_filename=f"panorama-v{next_ver}.jpg",
            content=stitched["pano_bytes"],
            mime_type="image/jpeg",
        )
        thumb_stored = storage.put_bytes(
            key_prefix=prefix,
            safe_filename=f"panorama-v{next_ver}-thumb.jpg",
            content=stitched["thumb_bytes"],
            mime_type="image/jpeg",
        )

        with transaction.atomic():
            # Preserve history: never delete prior versions; mark previous current as superseded only once a newer one is set current
            prior_current = scene.panorama_versions.filter(is_current=True).first()
            has_published_approved = prior_current and prior_current.state == PanoramaVersion.State.APPROVED

            pano = PanoramaVersion.objects.create(
                scene=scene,
                capture_session=session,
                version=next_ver,
                state=PanoramaVersion.State.REVIEW,
                storage_key=pano_stored.file_key,
                thumbnail_key=thumb_stored.file_key,
                projection="equirectangular",
                width_px=stitched["width_px"],
                height_px=stitched["height_px"],
                source_image_count=stitched["source_image_count"],
                engine=stitched["engine"],
                quality_report=stitched["quality_report"],
                # Keep currently approved panorama live if editing/reprocessing, or set new one current if none approved yet
                is_current=not has_published_approved,
                created_by=job.created_by,
                updated_by=job.created_by,
            )
            if not scene.thumbnail_storage_key:
                scene.thumbnail_storage_key = thumb_stored.file_key
                scene.save(update_fields=["thumbnail_storage_key", "updated_at"])

            session.status = CaptureSession.Status.COMPLETED
            session.completed_at = session.completed_at or timezone.now()
            session.save(update_fields=["status", "completed_at", "updated_at"])

            if scene.tour.status in (
                VirtualTour.Status.DRAFT,
                VirtualTour.Status.CAPTURING,
                VirtualTour.Status.PROCESSING,
                VirtualTour.Status.FAILED,
            ):
                scene.tour.status = VirtualTour.Status.REVIEW
                scene.tour.save(update_fields=["status", "updated_at"])

            job.state = ProcessingJob.State.SUCCEEDED
            job.progress = 100
            job.current_step = "پانوراما آماده بازبینی و تأیید است"
            job.completed_at = timezone.now()
            job.result = {
                "panorama_version_id": str(pano.id),
                "version": pano.version,
                "engine": pano.engine,
                "width_px": pano.width_px,
                "height_px": pano.height_px,
            }
            job.save()
        return pano
    except Exception as exc:
        job.state = ProcessingJob.State.FAILED
        job.error = str(exc)
        job.completed_at = timezone.now()
        job.current_step = "خطا در پردازش پانوراما"
        job.save(update_fields=["state", "error", "completed_at", "current_step", "updated_at"])
        raise


def enqueue_scene_panorama_processing(
    *,
    user: User,
    agency_id: Optional[UUID],
    scene_id: UUID,
    session_id: Optional[UUID] = None,
    reprocess: bool = False,
    idempotency_key: Optional[str] = None,
) -> ProcessingJob:
    scene = get_scene_for_user(user=user, agency_id=agency_id, scene_id=scene_id, require_edit=True)

    # Prevent duplicate concurrent jobs for the same scene
    active_job = ProcessingJob.objects.filter(
        scene=scene,
        job_type__in=[ProcessingJob.JobType.PANORAMA_STITCH, ProcessingJob.JobType.PANORAMA_REPROCESS],
        state__in=[ProcessingJob.State.QUEUED, ProcessingJob.State.RUNNING],
    ).first()
    if active_job:
        raise ConflictDomainError("یک پردازش پانوراما برای این اتاق هم‌اکنون در حال اجرا است.")

    if idempotency_key:
        prev = ProcessingJob.objects.filter(scene=scene, idempotency_key=idempotency_key).first()
        if prev:
            return prev

    target_session = (
        scene.capture_sessions.filter(id=session_id).first()
        if session_id
        else scene.capture_sessions.exclude(status=CaptureSession.Status.CANCELLED).order_by("-created_at").first()
    )
    if not target_session:
        raise ValidationDomainError("ابتدا یک جلسه عکاسی برای این اتاق ثبت کنید و حداقل ۲ تصویر آپلود نمایید.")
    if target_session.images.exclude(status__in=[CaptureImage.Status.REJECTED, CaptureImage.Status.REPLACED]).count() < 2:
        raise ValidationDomainError("برای شروع پردازش حداقل ۲ تصویر تأییدشده یا قابل قبول در جلسه عکاسی نیاز است.")

    job = ProcessingJob.objects.create(
        tour=scene.tour,
        scene=scene,
        job_type=ProcessingJob.JobType.PANORAMA_REPROCESS if reprocess else ProcessingJob.JobType.PANORAMA_STITCH,
        state=ProcessingJob.State.QUEUED,
        progress=0,
        current_step="در صف پردازش",
        idempotency_key=(idempotency_key or "")[:128],
        input_params={"session_id": str(target_session.id), "reprocess": reprocess},
        created_by=user,
        updated_by=user,
    )
    if scene.tour.status in (VirtualTour.Status.DRAFT, VirtualTour.Status.CAPTURING, VirtualTour.Status.FAILED):
        scene.tour.status = VirtualTour.Status.PROCESSING
        scene.tour.save(update_fields=["status", "updated_at"])

    record_audit_event(
        action="virtual_tour.panorama_process_enqueue",
        resource_type="ProcessingJob",
        resource_id=str(job.id),
        actor=user,
        agency_id=scene.tour.agency_id,
        after_state={"scene_id": str(scene.id), "job_type": job.job_type},
    )

    from apps.virtual_tours.tasks.jobs import process_panorama_stitch_task

    if _has_active_celery_worker():
        async_res = process_panorama_stitch_task.delay(str(job.id))
        job.celery_task_id = str(async_res.id)
        job.save(update_fields=["celery_task_id", "updated_at"])
    else:
        # Execute via Celery task entrypoint synchronously when worker daemon isn't attached (e.g. test suite)
        process_panorama_stitch_task.apply(args=[str(job.id)]).get()
        job.refresh_from_db()

    return job


@transaction.atomic
def upload_direct_equirectangular_panorama(
    *,
    user: User,
    agency_id: Optional[UUID],
    scene_id: UUID,
    filename: str,
    content_type: str,
    content: bytes,
) -> PanoramaVersion:
    """
    Allows uploading a pre-stitched 360° equirectangular panorama directly (e.g. from Ricoh Theta / Insta360),
    still enforcing review/approval workflow before publication.
    """
    scene = get_scene_for_user(user=user, agency_id=agency_id, scene_id=scene_id, require_edit=True)
    policy = get_capture_policy(tour=scene.tour)
    safe_name, mime, width, height, normalized_bytes = validate_capture_image_upload(
        filename=filename,
        content_type=content_type,
        content=content,
        max_mb=max(policy["max_upload_file_mb"], 40),
    )

    from io import BytesIO
    from PIL import Image

    aspect = width / max(1, height)
    if not 1.95 <= aspect <= 2.05:
        raise ValidationDomainError(
            "این فایل پانورامای ۳۶۰ درجه Equirectangular با نسبت تصویر نزدیک به ۲:۱ نیست. "
            "برای فایل‌های معمولی موبایل از عکاسی هدایت‌شده و دوخت تصاویر استفاده کنید؛ "
            "برای آپلود مستقیم، فایل خروجی ۳۶۰ درجه دوربین را انتخاب کنید."
        )

    with Image.open(BytesIO(normalized_bytes)) as im:
        thumb = im.convert("RGB").resize((800, 400), Image.Resampling.LANCZOS)
        tbuf = BytesIO()
        thumb.save(tbuf, format="JPEG", quality=82, optimize=True)
        thumb_bytes = tbuf.getvalue()

    next_ver = (scene.panorama_versions.order_by("-version").values_list("version", flat=True).first() or 0) + 1
    storage = get_storage_provider()
    prefix = f"private/virtual_tours/{scene.tour.agency_id}/{scene.tour_id}/panoramas/{scene.id}/v{next_ver}"
    pano_stored = storage.put_bytes(
        key_prefix=prefix,
        safe_filename=f"direct-v{next_ver}-{safe_name}",
        content=normalized_bytes,
        mime_type=mime,
    )
    thumb_stored = storage.put_bytes(
        key_prefix=prefix,
        safe_filename=f"direct-v{next_ver}-thumb.jpg",
        content=thumb_bytes,
        mime_type="image/jpeg",
    )

    prior_current = scene.panorama_versions.filter(is_current=True).first()
    has_approved = prior_current and prior_current.state == PanoramaVersion.State.APPROVED

    aspect = round(width / max(1, height), 3)
    pano = PanoramaVersion.objects.create(
        scene=scene,
        version=next_ver,
        state=PanoramaVersion.State.REVIEW,
        storage_key=pano_stored.file_key,
        thumbnail_key=thumb_stored.file_key,
        projection="equirectangular",
        width_px=width,
        height_px=height,
        source_image_count=1,
        engine="direct_equirectangular_upload",
        quality_report={
            "aspect_ratio": aspect,
            "is_2_to_1": 1.8 <= aspect <= 2.2,
            "resolution": f"{width}×{height}",
            "human_review_required": True,
        },
        is_current=not has_approved,
        created_by=user,
        updated_by=user,
    )
    if not scene.thumbnail_storage_key:
        scene.thumbnail_storage_key = thumb_stored.file_key
        scene.save(update_fields=["thumbnail_storage_key", "updated_at"])
    if scene.tour.status in (VirtualTour.Status.DRAFT, VirtualTour.Status.CAPTURING):
        scene.tour.status = VirtualTour.Status.REVIEW
        scene.tour.save(update_fields=["status", "updated_at"])

    record_audit_event(
        action="virtual_tour.panorama_direct_upload",
        resource_type="PanoramaVersion",
        resource_id=str(pano.id),
        actor=user,
        agency_id=scene.tour.agency_id,
        after_state={"scene_id": str(scene.id), "version": pano.version},
    )
    return pano


@transaction.atomic
def approve_scene_panorama(
    *,
    user: User,
    agency_id: Optional[UUID],
    scene_id: UUID,
    panorama_version_id: Optional[UUID] = None,
) -> PanoramaVersion:
    scene = get_scene_for_user(user=user, agency_id=agency_id, scene_id=scene_id, require_edit=False)
    assert_tour_approve_access(user=user, agency_id=agency_id, prop=scene.tour.property)

    pano = (
        scene.panorama_versions.filter(id=panorama_version_id).first()
        if panorama_version_id
        else scene.panorama_versions.order_by("-version").first()
    )
    if not pano:
        raise ValidationDomainError("نسخه پانورامای مورد نظر برای تأیید یافت نشد.")
    if pano.state == PanoramaVersion.State.FAILED:
        raise ValidationDomainError("نسخه ناموفق قابل تأیید نیست.")

    quality = pano.quality_report or {}
    if quality.get("coverage_complete") is False:
        detail = quality.get("coverage_warning") or "پوشش تصویر کامل نیست."
        raise ValidationDomainError(
            f"این پانوراما هنوز پوشش کافی ندارد و قابل تأیید نیست. {detail}"
        )

    # Mark previous current versions as superseded cleanly
    scene.panorama_versions.exclude(id=pano.id).filter(is_current=True).update(
        is_current=False, state=PanoramaVersion.State.SUPERSEDED
    )

    pano.state = PanoramaVersion.State.APPROVED
    pano.is_current = True
    pano.approved_by = user
    pano.approved_at = timezone.now()
    pano.rejection_reason = ""
    pano.updated_by = user
    pano.save()

    if pano.thumbnail_key:
        scene.thumbnail_storage_key = pano.thumbnail_key
        scene.save(update_fields=["thumbnail_storage_key", "updated_at"])

    record_audit_event(
        action="virtual_tour.panorama_approve",
        resource_type="PanoramaVersion",
        resource_id=str(pano.id),
        actor=user,
        agency_id=scene.tour.agency_id,
        after_state={"scene_id": str(scene.id), "version": pano.version},
    )
    return pano


@transaction.atomic
def reject_scene_panorama(
    *,
    user: User,
    agency_id: Optional[UUID],
    scene_id: UUID,
    reason: str,
    panorama_version_id: Optional[UUID] = None,
) -> PanoramaVersion:
    scene = get_scene_for_user(user=user, agency_id=agency_id, scene_id=scene_id, require_edit=False)
    assert_tour_approve_access(user=user, agency_id=agency_id, prop=scene.tour.property)

    pano = (
        scene.panorama_versions.filter(id=panorama_version_id).first()
        if panorama_version_id
        else scene.panorama_versions.order_by("-version").first()
    )
    if not pano:
        raise ValidationDomainError("نسخه پانوراما یافت نشد.")

    pano.state = PanoramaVersion.State.REJECTED
    pano.rejection_reason = (reason or "نیاز به بازبینی یا عکاسی مجدد").strip()
    pano.updated_by = user
    pano.save()

    record_audit_event(
        action="virtual_tour.panorama_reject",
        resource_type="PanoramaVersion",
        resource_id=str(pano.id),
        actor=user,
        agency_id=scene.tour.agency_id,
        after_state={"scene_id": str(scene.id), "version": pano.version, "reason": pano.rejection_reason},
    )
    return pano


@transaction.atomic
def restore_panorama_version(
    *,
    user: User,
    agency_id: Optional[UUID],
    scene_id: UUID,
    version_id: UUID,
) -> PanoramaVersion:
    scene = get_scene_for_user(user=user, agency_id=agency_id, scene_id=scene_id, require_edit=True)
    target = scene.panorama_versions.filter(id=version_id).first()
    if not target:
        raise ValidationDomainError("نسخه پانورامای درخواستی برای بازیابی یافت نشد.")
    if target.state == PanoramaVersion.State.FAILED:
        raise ValidationDomainError("نسخه ناموفق قابل بازیابی نیست.")
    if (target.quality_report or {}).get("coverage_complete") is False:
        detail = (target.quality_report or {}).get("coverage_warning") or "پوشش تصویر کامل نیست."
        raise ValidationDomainError(
            f"این نسخه به دلیل پوشش تصویری ناقص قابل بازیابی نیست. {detail}"
        )

    scene.panorama_versions.exclude(id=target.id).filter(is_current=True).update(
        is_current=False,
        state=PanoramaVersion.State.SUPERSEDED,
    )
    target.is_current = True
    if target.approved_at:
        target.state = PanoramaVersion.State.APPROVED
    elif target.state == PanoramaVersion.State.SUPERSEDED:
        target.state = PanoramaVersion.State.REVIEW
    target.updated_by = user
    target.save()

    if target.thumbnail_key:
        scene.thumbnail_storage_key = target.thumbnail_key
        scene.save(update_fields=["thumbnail_storage_key", "updated_at"])

    record_audit_event(
        action="virtual_tour.panorama_restore",
        resource_type="PanoramaVersion",
        resource_id=str(target.id),
        actor=user,
        agency_id=scene.tour.agency_id,
        after_state={"scene_id": str(scene.id), "version": target.version, "state": target.state},
    )
    return target


def retry_processing_job(*, user: User, agency_id: Optional[UUID], job_id: UUID) -> ProcessingJob:
    job = get_processing_job_for_user(user=user, agency_id=agency_id, job_id=job_id, require_edit=True)
    limits = get_tour_limits(agency_id=job.tour.agency_id, tour=job.tour)
    if job.retry_count >= limits["max_job_retries"]:
        raise ValidationDomainError(f"سقف مجاز تلاش مجدد ({limits['max_job_retries']}) به پایان رسیده است.")
    if job.state in (ProcessingJob.State.QUEUED, ProcessingJob.State.RUNNING):
        raise ConflictDomainError("این پردازش هم‌اکنون در حال اجرا است.")

    job.state = ProcessingJob.State.QUEUED
    job.retry_count += 1
    job.error = ""
    job.progress = 0
    job.current_step = "در صف اجرای مجدد"
    job.save(update_fields=["state", "retry_count", "error", "progress", "current_step", "updated_at"])

    if job.job_type in (ProcessingJob.JobType.PANORAMA_STITCH, ProcessingJob.JobType.PANORAMA_REPROCESS):
        from apps.virtual_tours.tasks.jobs import process_panorama_stitch_task

        if _has_active_celery_worker():
            res = process_panorama_stitch_task.delay(str(job.id))
            job.celery_task_id = str(res.id)
            job.save(update_fields=["celery_task_id", "updated_at"])
        else:
            process_panorama_stitch_task.apply(args=[str(job.id)]).get()
            job.refresh_from_db()
    elif job.job_type == ProcessingJob.JobType.MODEL_BUILD:
        from apps.virtual_tours.tasks.jobs import build_3d_model_task

        if _has_active_celery_worker():
            res = build_3d_model_task.delay(str(job.id))
            job.celery_task_id = str(res.id)
            job.save(update_fields=["celery_task_id", "updated_at"])
        else:
            build_3d_model_task.apply(args=[str(job.id)]).get()
            job.refresh_from_db()
    elif job.job_type == ProcessingJob.JobType.SCAN_PROCESS:
        from apps.virtual_tours.tasks.jobs import process_scan_asset_task

        if _has_active_celery_worker():
            res = process_scan_asset_task.delay(str(job.id))
            job.celery_task_id = str(res.id)
            job.save(update_fields=["celery_task_id", "updated_at"])
        else:
            process_scan_asset_task.apply(args=[str(job.id)]).get()
            job.refresh_from_db()
    return job


def cancel_processing_job(*, user: User, agency_id: Optional[UUID], job_id: UUID) -> ProcessingJob:
    job = get_processing_job_for_user(user=user, agency_id=agency_id, job_id=job_id, require_edit=True)
    if job.state in (ProcessingJob.State.SUCCEEDED, ProcessingJob.State.FAILED, ProcessingJob.State.CANCELLED):
        return job
    job.state = ProcessingJob.State.CANCELLED
    job.completed_at = timezone.now()
    job.current_step = "لغوشده توسط کاربر"
    job.save(update_fields=["state", "completed_at", "current_step", "updated_at"])
    return job
