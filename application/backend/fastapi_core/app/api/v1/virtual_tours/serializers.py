from apps.virtual_tours.models import (
    CaptureGuideStep,
    CaptureImage,
    CaptureSession,
    Floor,
    FloorPlanAsset,
    GeneratedModelAsset,
    Hotspot,
    PanoramaVersion,
    ProcessingJob,
    RoomGeometry,
    ScanAsset,
    Scene,
    SceneLink,
    TourPublication,
    TourQualityReport,
    VirtualTour,
    WallOpening,
    WallSegment,
)
from apps.virtual_tours.policies.access import build_private_file_url
from apps.virtual_tours.services.quality_service import evaluate_capture_session_quality
from apps.virtual_tours.services.settings_service import (
    get_capture_policy,
    get_room_types_catalog,
    get_tour_limits,
)


def serialize_floor(floor: Floor) -> dict:
    return {
        "id": str(floor.id),
        "tour_id": str(floor.tour_id),
        "title": floor.title,
        "order": floor.order,
        "elevation_m": str(floor.elevation_m),
        "description": floor.description,
        "created_at": floor.created_at.isoformat(),
    }


def serialize_floorplan(fp: FloorPlanAsset) -> dict:
    tour_id = str(fp.tour_id)
    return {
        "id": str(fp.id),
        "tour_id": tour_id,
        "floor_id": str(fp.floor_id),
        "floor_title": fp.floor.title,
        "file_type": fp.file_type,
        "filename": fp.filename,
        "width_px": fp.width_px,
        "height_px": fp.height_px,
        "scale_m_per_px": fp.scale_m_per_px,
        "calibration_data": fp.calibration_data or {},
        "file_url": build_private_file_url(kind="floorplan-preview", object_id=str(fp.id), tour_id=tour_id, signed=True),
        "created_at": fp.created_at.isoformat(),
    }


def serialize_wall_opening(op: WallOpening) -> dict:
    return {
        "id": str(op.id),
        "wall_id": str(op.wall_id),
        "kind": op.kind,
        "offset_ratio": op.offset_ratio,
        "width_m": op.width_m,
        "height_m": op.height_m,
        "sill_height_m": op.sill_height_m,
    }


def serialize_wall_segment(wall: WallSegment) -> dict:
    return {
        "id": str(wall.id),
        "tour_id": str(wall.tour_id),
        "floor_id": str(wall.floor_id),
        "start_x": wall.start_x,
        "start_y": wall.start_y,
        "end_x": wall.end_x,
        "end_y": wall.end_y,
        "thickness_m": wall.thickness_m,
        "height_m": wall.height_m,
        "is_exterior": wall.is_exterior,
        "openings": [serialize_wall_opening(op) for op in wall.openings.all()],
    }


def serialize_room_geometry(room: RoomGeometry) -> dict:
    return {
        "id": str(room.id),
        "tour_id": str(room.tour_id),
        "floor_id": str(room.floor_id),
        "scene_id": str(room.scene_id) if room.scene_id else None,
        "scene_title": room.scene.title if room.scene_id and room.scene else None,
        "label": room.label,
        "room_type": room.room_type,
        "polygon_points": room.polygon_points or [],
        "area_sqm": str(room.area_sqm),
        "perimeter_m": str(room.perimeter_m),
        "height_m": str(room.height_m),
        "source": room.source,
        "color_hex": room.color_hex,
    }


def serialize_generated_model_asset(asset: GeneratedModelAsset) -> dict:
    tour_id = str(asset.tour_id)
    return {
        "id": str(asset.id),
        "tour_id": tour_id,
        "version": asset.version,
        "format": asset.format,
        "state": asset.state,
        "geometry_source": asset.geometry_source,
        "estimated_accuracy": asset.estimated_accuracy,
        "total_area_sqm": str(asset.total_area_sqm),
        "file_url": build_private_file_url(kind="model-glb", object_id=str(asset.id), tour_id=tour_id, signed=True),
        "size_bytes": asset.size_bytes,
        "metadata": asset.metadata or {},
        "is_current": asset.is_current,
        "created_at": asset.created_at.isoformat(),
    }


def serialize_scan_asset(scan: ScanAsset) -> dict:
    tour_id = str(scan.tour_id)
    res = getattr(scan, "processing_result", None)
    return {
        "id": str(scan.id),
        "tour_id": tour_id,
        "floor_id": str(scan.floor_id) if scan.floor_id else None,
        "floor_title": scan.floor.title if scan.floor_id and scan.floor else None,
        "scene_id": str(scan.scene_id) if scan.scene_id else None,
        "scene_title": scan.scene.title if scan.scene_id and scan.scene else None,
        "format": scan.format,
        "filename": scan.filename,
        "size_bytes": scan.size_bytes,
        "status": scan.status,
        "source_device": scan.source_device,
        "points_count": scan.points_count,
        "bounding_box": scan.bounding_box or {},
        "raw_file_url": build_private_file_url(kind="scan-raw", object_id=str(scan.id), tour_id=tour_id, signed=True),
        "preview_glb_url": (
            build_private_file_url(kind="scan-preview-glb", object_id=str(scan.id), tour_id=tour_id, signed=True)
            if scan.preview_glb_key
            else None
        ),
        "density_map_url": (
            build_private_file_url(kind="scan-density-map", object_id=str(scan.id), tour_id=tour_id, signed=True)
            if scan.density_map_key
            else None
        ),
        "processing_notes": scan.processing_notes,
        "processing_result": (
            {
                "raw_points_count": res.raw_points_count,
                "downsampled_points_count": res.downsampled_points_count,
                "outlier_points_count": res.outlier_points_count,
                "estimated_footprint_sqm": str(res.estimated_footprint_sqm),
                "point_density_per_sqm": res.point_density_per_sqm,
                "height_stats": res.height_stats or {},
                "engine": res.engine,
                "notes": res.notes,
            }
            if res
            else None
        ),
        "created_at": scan.created_at.isoformat(),
    }


def serialize_hotspot(hs: Hotspot) -> dict:
    return {
        "id": str(hs.id),
        "scene_id": str(hs.scene_id),
        "kind": hs.kind,
        "title": hs.title,
        "body": hs.body,
        "yaw": hs.yaw,
        "pitch": hs.pitch,
        "target_scene_id": str(hs.target_scene_id) if hs.target_scene_id else None,
        "target_scene_title": hs.target_scene.title if hs.target_scene_id and hs.target_scene else None,
        "metadata": hs.metadata or {},
        "created_at": hs.created_at.isoformat(),
    }


def serialize_scene_link(lnk: SceneLink) -> dict:
    return {
        "id": str(lnk.id),
        "tour_id": str(lnk.tour_id),
        "source_scene_id": str(lnk.source_scene_id),
        "source_scene_title": lnk.source_scene.title,
        "target_scene_id": str(lnk.target_scene_id),
        "target_scene_title": lnk.target_scene.title,
        "yaw": lnk.yaw,
        "pitch": lnk.pitch,
        "title": lnk.title or lnk.target_scene.title,
        "bidirectional": lnk.bidirectional,
        "reverse_yaw": lnk.reverse_yaw,
        "created_at": lnk.created_at.isoformat(),
    }


def serialize_panorama_version(pano: PanoramaVersion, *, tour_id: str) -> dict:
    return {
        "id": str(pano.id),
        "scene_id": str(pano.scene_id),
        "capture_session_id": str(pano.capture_session_id) if pano.capture_session_id else None,
        "version": pano.version,
        "state": pano.state,
        "projection": pano.projection,
        "width_px": pano.width_px,
        "height_px": pano.height_px,
        "source_image_count": pano.source_image_count,
        "engine": pano.engine,
        "quality_report": pano.quality_report or {},
        "is_current": pano.is_current,
        "panorama_url": (
            build_private_file_url(kind="panorama", object_id=str(pano.id), tour_id=tour_id, signed=True)
            if pano.storage_key
            else None
        ),
        "thumbnail_url": (
            build_private_file_url(kind="panorama-thumb", object_id=str(pano.id), tour_id=tour_id, signed=True)
            if pano.thumbnail_key
            else None
        ),
        "approved_by_name": pano.approved_by.full_name if pano.approved_by else None,
        "approved_at": pano.approved_at.isoformat() if pano.approved_at else None,
        "rejection_reason": pano.rejection_reason,
        "created_at": pano.created_at.isoformat(),
    }


def serialize_capture_image(img: CaptureImage, *, tour_id: str) -> dict:
    return {
        "id": str(img.id),
        "session_id": str(img.session_id),
        "scene_id": str(img.scene_id),
        "sequence": img.sequence,
        "filename": img.filename,
        "mime_type": img.mime_type,
        "size_bytes": img.size_bytes,
        "width": img.width,
        "height": img.height,
        "status": img.status,
        "analysis": img.analysis or {},
        "yaw": img.yaw,
        "pitch": img.pitch,
        "image_url": build_private_file_url(kind="capture", object_id=str(img.id), tour_id=tour_id, signed=True),
        "captured_at": img.captured_at.isoformat(),
    }


def serialize_capture_guide_step(step: CaptureGuideStep, *, tour_id: str) -> dict:
    return {
        "id": str(step.id),
        "sequence": step.sequence,
        "yaw": step.yaw,
        "pitch": step.pitch,
        "label": step.label,
        "required": step.required,
        "expected_overlap_percent": step.expected_overlap_percent,
        "state": step.state,
        "guidance": step.guidance,
        "image_id": str(step.image_id) if step.image_id else None,
        "image_url": (
            build_private_file_url(kind="capture", object_id=str(step.image_id), tour_id=tour_id, signed=True)
            if step.image_id
            else None
        ),
    }


def serialize_capture_session(session: CaptureSession) -> dict:
    tour_id = str(session.tour_id)
    steps = list(session.guide_steps.select_related("image").order_by("sequence"))
    images = list(session.images.exclude(status=CaptureImage.Status.REPLACED).order_by("sequence"))
    summary = evaluate_capture_session_quality(session)
    return {
        "id": str(session.id),
        "tour_id": tour_id,
        "scene_id": str(session.scene_id),
        "scene_title": session.scene.title,
        "status": session.status,
        "device_info": session.device_info or {},
        "capture_config": session.capture_config or {},
        "started_at": session.started_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "summary": summary,
        "steps": [serialize_capture_guide_step(s, tour_id=tour_id) for s in steps],
        "images": [serialize_capture_image(img, tour_id=tour_id) for img in images],
    }


def serialize_scene(scene: Scene, *, include_details: bool = True) -> dict:
    tour_id = str(scene.tour_id)
    panos = list(scene.panorama_versions.select_related("approved_by").order_by("-version"))
    current_pano = next((p for p in panos if p.is_current), panos[0] if panos else None)
    thumb_url = None
    if current_pano and current_pano.thumbnail_key:
        thumb_url = build_private_file_url(
            kind="panorama-thumb", object_id=str(current_pano.id), tour_id=tour_id, signed=True
        )
    data = {
        "id": str(scene.id),
        "tour_id": tour_id,
        "floor_id": str(scene.floor_id),
        "floor_title": scene.floor.title,
        "title": scene.title,
        "room_type": scene.room_type,
        "description": scene.description,
        "order": scene.order,
        "is_start_scene": scene.is_start_scene,
        "active": scene.active,
        "initial_yaw": scene.initial_yaw,
        "initial_pitch": scene.initial_pitch,
        "thumbnail_url": thumb_url,
        "width_m": str(scene.width_m) if scene.width_m is not None else None,
        "length_m": str(scene.length_m) if scene.length_m is not None else None,
        "height_m": str(scene.height_m) if scene.height_m is not None else None,
        "geometry_source": scene.geometry_source,
        "current_panorama": serialize_panorama_version(current_pano, tour_id=tour_id) if current_pano else None,
        "panorama_count": len(panos),
        "capture_sessions_count": scene.capture_sessions.count(),
        "hotspots_count": scene.hotspots.count(),
        "created_at": scene.created_at.isoformat(),
    }
    if include_details:
        data["panoramas"] = [serialize_panorama_version(p, tour_id=tour_id) for p in panos]
        data["hotspots"] = [
            serialize_hotspot(hs) for hs in scene.hotspots.select_related("target_scene").order_by("created_at")
        ]
        data["outgoing_links"] = [
            serialize_scene_link(lnk)
            for lnk in scene.outgoing_links.select_related("source_scene", "target_scene").order_by("created_at")
        ]
    return data


def serialize_processing_job(job: ProcessingJob) -> dict:
    return {
        "id": str(job.id),
        "tour_id": str(job.tour_id),
        "scene_id": str(job.scene_id) if job.scene_id else None,
        "scene_title": job.scene.title if job.scene_id and job.scene else None,
        "job_type": job.job_type,
        "state": job.state,
        "progress": job.progress,
        "current_step": job.current_step,
        "celery_task_id": job.celery_task_id,
        "error": job.error,
        "result": job.result or {},
        "retry_count": job.retry_count,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "created_at": job.created_at.isoformat(),
    }


def serialize_quality_report(report: TourQualityReport) -> dict:
    return {
        "id": str(report.id),
        "tour_id": str(report.tour_id),
        "is_ready_to_publish": report.is_ready_to_publish,
        "blocking_issues_count": report.blocking_issues_count,
        "warning_issues_count": report.warning_issues_count,
        "report_data": report.report_data or {},
        "created_at": report.created_at.isoformat(),
    }


def serialize_publication(pub: TourPublication) -> dict:
    return {
        "id": str(pub.id),
        "tour_id": str(pub.tour_id),
        "version": pub.version,
        "is_active": pub.is_active,
        "public_slug": pub.public_slug,
        "published_by_name": pub.published_by.full_name if pub.published_by else None,
        "published_at": pub.published_at.isoformat(),
        "unpublished_at": pub.unpublished_at.isoformat() if pub.unpublished_at else None,
        "scenes_count": len((pub.snapshot_json or {}).get("scenes") or []),
        "floors_count": len((pub.snapshot_json or {}).get("floors") or []),
    }


def serialize_virtual_tour_detail(tour: VirtualTour) -> dict:
    floors = list(tour.floors.order_by("order", "created_at"))
    scenes = list(
        tour.scenes.select_related("floor")
        .prefetch_related("panorama_versions", "panorama_versions__approved_by", "hotspots", "hotspots__target_scene", "outgoing_links", "outgoing_links__target_scene", "outgoing_links__source_scene")
        .order_by("floor__order", "order", "created_at")
    )
    links = list(tour.links.select_related("source_scene", "target_scene").order_by("created_at"))
    active_pub = tour.publications.filter(is_active=True).order_by("-version").first()
    latest_report = tour.quality_reports.order_by("-created_at").first()
    jobs = list(tour.processing_jobs.select_related("scene").order_by("-created_at")[:25])
    floorplans = list(tour.floorplans.filter(is_active=True).select_related("floor").order_by("floor__order", "-created_at"))
    rooms = list(tour.room_geometries.select_related("scene", "floor").order_by("floor__order", "created_at"))
    walls = list(tour.wall_segments.prefetch_related("openings").order_by("floor__order", "created_at"))
    models = list(tour.generated_models.order_by("-version"))
    current_model = next((m for m in models if m.is_current), models[0] if models else None)
    scans = list(tour.scans.select_related("floor", "scene", "processing_result").order_by("-created_at"))

    return {
        "id": str(tour.id),
        "property_id": str(tour.property_id),
        "property_code": tour.property.property_code,
        "property_title": tour.property.title,
        "property_status": tour.property.status,
        "property_visibility": tour.property.visibility,
        "agency_id": str(tour.agency_id),
        "branch_id": str(tour.branch_id) if tour.branch_id else None,
        "title": tour.title,
        "description": tour.description,
        "status": tour.status,
        "settings_override": tour.settings_override or {},
        "published_at": tour.published_at.isoformat() if tour.published_at else None,
        "archived_at": tour.archived_at.isoformat() if tour.archived_at else None,
        "created_at": tour.created_at.isoformat(),
        "updated_at": tour.updated_at.isoformat(),
        "floors": [serialize_floor(f) for f in floors],
        "scenes": [serialize_scene(s, include_details=True) for s in scenes],
        "links": [serialize_scene_link(l) for l in links],
        "floorplans": [serialize_floorplan(fp) for fp in floorplans],
        "rooms": [serialize_room_geometry(r) for r in rooms],
        "walls": [serialize_wall_segment(w) for w in walls],
        "generated_models": [serialize_generated_model_asset(m) for m in models],
        "current_model": serialize_generated_model_asset(current_model) if current_model else None,
        "scans": [serialize_scan_asset(scn) for scn in scans],
        "active_publication": serialize_publication(active_pub) if active_pub else None,
        "latest_quality_report": serialize_quality_report(latest_report) if latest_report else None,
        "recent_jobs": [serialize_processing_job(j) for j in jobs],
        "config": {
            "room_types": get_room_types_catalog(tour.agency_id),
            "capture_policy": get_capture_policy(tour=tour),
            "limits": get_tour_limits(agency_id=tour.agency_id, tour=tour),
        },
    }
