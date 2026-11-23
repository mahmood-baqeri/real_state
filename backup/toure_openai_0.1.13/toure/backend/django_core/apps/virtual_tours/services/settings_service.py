from typing import Any, Optional
from uuid import UUID
from apps.settings.services import get_setting_value
from apps.virtual_tours.models import Scene, VirtualTour


def get_vt_setting(
    key: str,
    default: Any,
    *,
    agency_id: Optional[UUID] = None,
    tour: Optional[VirtualTour] = None,
) -> Any:
    """
    Resolves Virtual Tour dynamic configuration in strict hierarchy:
    Tour settings_override -> Agency SystemSetting -> Global SystemSetting -> default fallback.
    """
    if tour is not None:
        override_val = (tour.settings_override or {}).get(key)
        if override_val is not None:
            return override_val
        if agency_id is None:
            agency_id = tour.agency_id
    return get_setting_value(key, default, agency_id=agency_id)


def get_room_types_catalog(agency_id: Optional[UUID] = None) -> list[dict[str, str]]:
    default_list = [{"code": c, "label": l} for c, l in Scene.DEFAULT_ROOM_TYPES]
    configured = get_vt_setting("virtual_tour.room_types", default_list, agency_id=agency_id)
    if isinstance(configured, list) and configured:
        cleaned = []
        for item in configured:
            if isinstance(item, dict) and item.get("code") and item.get("label"):
                cleaned.append({"code": str(item["code"]), "label": str(item["label"])})
        if cleaned:
            return cleaned
    return default_list


def get_capture_policy(
    *,
    agency_id: Optional[UUID] = None,
    tour: Optional[VirtualTour] = None,
) -> dict[str, Any]:
    horizontal_steps = int(get_vt_setting("virtual_tour.capture_horizontal_steps", 12, agency_id=agency_id, tour=tour) or 12)
    horizontal_steps = max(4, min(24, horizontal_steps))
    require_ceiling_floor = bool(
        get_vt_setting("virtual_tour.capture_require_ceiling_floor", True, agency_id=agency_id, tour=tour)
    )
    target_overlap = float(
        get_vt_setting("virtual_tour.capture_target_overlap_percent", 35, agency_id=agency_id, tour=tour) or 35
    )
    min_usable_images = int(
        get_vt_setting("virtual_tour.min_usable_images_for_stitch", 8, agency_id=agency_id, tour=tour) or 8
    )
    min_width = int(get_vt_setting("virtual_tour.min_image_width_px", 800, agency_id=agency_id, tour=tour) or 800)
    min_height = int(get_vt_setting("virtual_tour.min_image_height_px", 600, agency_id=agency_id, tour=tour) or 600)
    max_file_mb = int(get_vt_setting("virtual_tour.max_upload_file_mb", 20, agency_id=agency_id, tour=tour) or 20)
    return {
        "horizontal_steps": horizontal_steps,
        "require_ceiling_floor": require_ceiling_floor,
        "target_overlap_percent": target_overlap,
        "min_usable_images_for_stitch": max(4, min_usable_images),
        "min_image_width_px": min_width,
        "min_image_height_px": min_height,
        "max_upload_file_mb": max_file_mb,
        "min_blur_score": float(get_vt_setting("virtual_tour.qc_min_blur_score", 45.0, agency_id=agency_id, tour=tour) or 45.0),
        "min_brightness": float(get_vt_setting("virtual_tour.qc_min_brightness", 35.0, agency_id=agency_id, tour=tour) or 35.0),
        "max_brightness": float(get_vt_setting("virtual_tour.qc_max_brightness", 225.0, agency_id=agency_id, tour=tour) or 225.0),
        "min_contrast": float(get_vt_setting("virtual_tour.qc_min_contrast", 18.0, agency_id=agency_id, tour=tour) or 18.0),
        "panorama_engine": str(get_vt_setting("virtual_tour.stitching_engine", "opencv", agency_id=agency_id, tour=tour) or "opencv"),
        "panorama_output_width": int(get_vt_setting("virtual_tour.panorama_output_width_px", 2048, agency_id=agency_id, tour=tour) or 2048),
    }


def get_tour_limits(agency_id: Optional[UUID] = None, tour: Optional[VirtualTour] = None) -> dict[str, Any]:
    return {
        "module_enabled": bool(get_vt_setting("virtual_tour.enabled", True, agency_id=agency_id, tour=tour)),
        "max_floors": int(get_vt_setting("virtual_tour.max_floors_per_tour", 10, agency_id=agency_id, tour=tour) or 10),
        "max_scenes": int(get_vt_setting("virtual_tour.max_scenes_per_tour", 40, agency_id=agency_id, tour=tour) or 40),
        "require_manager_approval": bool(
            get_vt_setting("virtual_tour.require_manager_approval", True, agency_id=agency_id, tour=tour)
        ),
        "require_verified_property": bool(
            get_vt_setting("virtual_tour.require_property_verification", True, agency_id=agency_id, tour=tour)
        ),
        "job_timeout_seconds": int(
            get_vt_setting("virtual_tour.job_timeout_seconds", 300, agency_id=agency_id, tour=tour) or 300
        ),
        "max_job_retries": int(
            get_vt_setting("virtual_tour.max_job_retries", 2, agency_id=agency_id, tour=tour) or 2
        ),
    }
