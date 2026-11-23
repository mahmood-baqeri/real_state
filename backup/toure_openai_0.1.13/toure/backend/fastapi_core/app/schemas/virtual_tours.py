from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class VirtualTourCreateBody(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    description: str = ""
    create_default_floor: bool = True


class VirtualTourPatchBody(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    settings_override: Optional[dict[str, Any]] = None


class FloorCreateBody(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    order: Optional[int] = Field(default=None, ge=0)
    elevation_m: float = 0.0
    description: str = ""


class FloorPatchBody(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    order: Optional[int] = Field(default=None, ge=0)
    elevation_m: Optional[float] = None
    description: Optional[str] = None


class SceneCreateBody(BaseModel):
    floor_id: UUID
    title: str = Field(..., min_length=1, max_length=140)
    room_type: str = "living_room"
    description: str = ""
    order: Optional[int] = Field(default=None, ge=0)
    is_start_scene: bool = False
    initial_yaw: float = 0.0
    initial_pitch: float = 0.0


class ScenePatchBody(BaseModel):
    floor_id: Optional[UUID] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=140)
    room_type: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = Field(default=None, ge=0)
    active: Optional[bool] = None
    is_start_scene: Optional[bool] = None
    initial_yaw: Optional[float] = None
    initial_pitch: Optional[float] = None


class CaptureSessionCreateBody(BaseModel):
    device_info: dict[str, Any] = Field(default_factory=dict)
    allow_partial_stitch: bool = False


class ProcessSceneBody(BaseModel):
    session_id: Optional[UUID] = None
    reprocess: bool = False


class PanoramaApproveBody(BaseModel):
    panorama_version_id: Optional[UUID] = None


class PanoramaRejectBody(BaseModel):
    panorama_version_id: Optional[UUID] = None
    reason: str = Field(..., min_length=3, max_length=500)


class SceneLinkCreateBody(BaseModel):
    source_scene_id: UUID
    target_scene_id: UUID
    yaw: float = 0.0
    pitch: float = -5.0
    title: str = ""
    bidirectional: bool = True


class HotspotCreateBody(BaseModel):
    kind: str = "info"
    title: str = Field(..., min_length=1, max_length=140)
    body: str = ""
    yaw: float = 0.0
    pitch: float = 0.0
    target_scene_id: Optional[UUID] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HotspotPatchBody(BaseModel):
    kind: Optional[str] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=140)
    body: Optional[str] = None
    yaw: Optional[float] = None
    pitch: Optional[float] = None
    target_scene_id: Optional[UUID] = None
    metadata: Optional[dict[str, Any]] = None


class TourAnalyticsEventBody(BaseModel):
    event_type: str
    session_key: str = Field(..., min_length=3, max_length=64)
    scene_id: Optional[UUID] = None
    hotspot_id: Optional[UUID] = None
    device_type: str = "desktop"
    duration_sec: int = Field(default=0, ge=0, le=86400)


class FloorPlanCalibrateBody(BaseModel):
    point_a: list[float] = Field(..., min_length=2, max_length=2)
    point_b: list[float] = Field(..., min_length=2, max_length=2)
    real_distance_m: float = Field(..., gt=0.05, le=500.0)


class RoomGeometryUpsertBody(BaseModel):
    floor_id: UUID
    scene_id: Optional[UUID] = None
    floorplan_id: Optional[UUID] = None
    label: str = Field(..., min_length=1, max_length=140)
    room_type: str = "living_room"
    polygon_points: list[list[float]] = Field(..., min_length=3)
    height_m: Optional[float] = Field(default=None, ge=1.8, le=12.0)
    color_hex: Optional[str] = Field(default=None, max_length=16)


class WallSegmentCreateBody(BaseModel):
    floor_id: UUID
    floorplan_id: Optional[UUID] = None
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    thickness_m: Optional[float] = Field(default=None, ge=0.05, le=1.0)
    height_m: Optional[float] = Field(default=None, ge=1.5, le=12.0)
    is_exterior: bool = False


class WallOpeningCreateBody(BaseModel):
    kind: str = "door"
    offset_ratio: float = Field(default=0.5, ge=0.05, le=0.95)
    width_m: float = Field(default=0.95, ge=0.2, le=12.0)
    height_m: float = Field(default=2.10, ge=0.4, le=6.0)
    sill_height_m: float = Field(default=0.0, ge=0.0, le=2.5)


class RoomMeasurementCreateBody(BaseModel):
    label: str = Field(..., min_length=1, max_length=120)
    start_point: list[float] = Field(..., min_length=2, max_length=2)
    end_point: list[float] = Field(..., min_length=2, max_length=2)


class GenerateDollhouseBody(BaseModel):
    wall_height_m: Optional[float] = Field(default=None, ge=1.8, le=12.0)
    wall_thickness_m: Optional[float] = Field(default=None, ge=0.05, le=1.0)


class ModelRejectBody(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)
