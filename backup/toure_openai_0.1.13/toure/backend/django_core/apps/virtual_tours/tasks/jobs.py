from uuid import UUID
from celery import shared_task


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def process_panorama_stitch_task(self, job_id: str) -> dict:
    from apps.virtual_tours.services.panorama_service import execute_panorama_stitch_job

    pano = execute_panorama_stitch_job(job_id=UUID(job_id))
    return {
        "panorama_version_id": str(pano.id),
        "version": pano.version,
        "engine": pano.engine,
        "state": pano.state,
    }


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def build_3d_model_task(self, job_id: str) -> dict:
    from apps.virtual_tours.services.geometry_service import execute_dollhouse_build_job

    asset = execute_dollhouse_build_job(job_id=UUID(job_id))
    return {
        "model_asset_id": str(asset.id),
        "version": asset.version,
        "format": asset.format,
        "size_bytes": asset.size_bytes,
    }


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def process_scan_asset_task(self, job_id: str) -> dict:
    from apps.virtual_tours.services.scan_service import execute_scan_process_job

    scan = execute_scan_process_job(job_id=UUID(job_id))
    return {
        "scan_id": str(scan.id),
        "format": scan.format,
        "status": scan.status,
        "points_count": scan.points_count,
    }
