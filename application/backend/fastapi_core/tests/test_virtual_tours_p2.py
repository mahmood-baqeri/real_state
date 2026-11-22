import io
import os
import sys
import uuid
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = ROOT_DIR / "backend" / "django_core"
FASTAPI_DIR = ROOT_DIR / "backend" / "fastapi_core"
for p in (str(BACKEND_DIR), str(FASTAPI_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

from app.main import app  # noqa: E402

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def bootstrap_db(django_db_setup, django_db_blocker):
    from django.core.cache import cache
    from django.core.management import call_command

    with django_db_blocker.unblock():
        cache.clear()
        call_command("seed_demo", quiet=True)


def _login(client: TestClient, phone: str, password: str) -> dict:
    res = client.post("/api/v1/auth/login", json={"phone_number": phone, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["data"]


def _agency_headers(auth_data: dict) -> dict:
    return {
        "Authorization": f"Bearer {auth_data['access']}",
        "X-Agency-ID": auth_data["user"]["memberships"][0]["agency_id"],
    }


def _create_draft_property(client: TestClient, headers: dict, suffix: str) -> dict:
    res = client.post(
        "/api/v1/properties",
        headers=headers,
        json={
            "property_code": f"P2VT-{suffix}",
            "title": f"آپارتمان اسکن LiDAR {suffix}",
            "property_type_id": "APARTMENT",
            "deal_type_id": "SALE",
            "visibility": "PRIVATE_AGENCY",
            "built_area_sqm": "185",
            "bedrooms": 3,
            "bathrooms": 2,
            "total_price": "26000000000",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["data"]


def _make_room_ascii_ply() -> bytes:
    pts = []
    # 5m x 4m x 2.8m room box + 2 far outliers to test robust MAD filtering
    for ix in range(11):
        x = ix * 0.5
        for iz in range(9):
            z = iz * 0.5
            pts.append((x, 0.0, z, 140, 120, 100))
            pts.append((x, 2.8, z, 230, 235, 240))
    for iy in range(1, 6):
        y = iy * 0.45
        for ix in range(11):
            x = ix * 0.5
            pts.append((x, y, 0.0, 210, 215, 220))
            pts.append((x, y, 4.0, 210, 215, 220))
    pts.append((120.0, 95.0, -140.0, 255, 0, 0))
    pts.append((-150.0, 80.0, 110.0, 255, 0, 0))

    header = [
        "ply",
        "format ascii 1.0",
        f"element vertex {len(pts)}",
        "property float x",
        "property float y",
        "property float z",
        "property uchar red",
        "property uchar green",
        "property uchar blue",
        "end_header",
    ]
    body = "\n".join(f"{x:.3f} {y:.3f} {z:.3f} {r} {g} {b}" for x, y, z, r, g, b in pts)
    return ("\n".join(header) + "\n" + body + "\n").encode("utf-8")


def _make_uint16_depth_png(width: int = 120, height: int = 90) -> bytes:
    # uint16 depth map in millimeters (1.5m .. 4.5m gradient)
    xs = np.linspace(1500, 4500, width, dtype=np.uint16)
    depth = np.tile(xs, (height, 1))
    ok_enc, buf = cv2.imencode(".png", depth)
    assert ok_enc
    return buf.tobytes()


def _make_wavefront_obj_box() -> bytes:
    return (
        "o room_box\n"
        "v 0 0 0\n"
        "v 4 0 0\n"
        "v 4 0 3\n"
        "v 0 0 3\n"
        "v 0 2.9 0\n"
        "v 4 2.9 0\n"
        "v 4 2.9 3\n"
        "v 0 2.9 3\n"
        "f 1 2 3 4\n"
        "f 5 6 7 8\n"
        "f 1 2 6 5\n"
        "f 2 3 7 6\n"
    ).encode("utf-8")


def test_p2_seeded_demo_scan_and_analytics():
    client = TestClient(app)
    mgr = _login(client, "09121111111", "Manager@12345")
    mgr_headers = _agency_headers(mgr)

    pub_props = client.get("/api/v1/properties/public?page=1&page_size=20")
    assert pub_props.status_code == 200
    demo_prop = next((p for p in pub_props.json()["data"] if p.get("property_code") == "PN-1001"), None)
    assert demo_prop is not None

    tour_res = client.get(f"/api/v1/properties/{demo_prop['id']}/virtual-tour", headers=mgr_headers)
    assert tour_res.status_code == 200
    tour = tour_res.json()["data"]

    scans = tour.get("scans") or []
    assert len(scans) >= 1
    lidar_scan = scans[0]
    assert lidar_scan["status"] == "validated"
    assert lidar_scan["source_device"] == "lidar_ios"
    assert lidar_scan["points_count"] > 100
    assert lidar_scan["preview_glb_url"]
    assert lidar_scan["density_map_url"]

    glb_res = client.get(lidar_scan["preview_glb_url"])
    assert glb_res.status_code == 200
    assert glb_res.content[:4] == b"glTF"

    png_res = client.get(lidar_scan["density_map_url"])
    assert png_res.status_code == 200
    assert png_res.content[:8] == b"\x89PNG\r\n\x1a\n"

    qr_res = client.get(f"/api/v1/virtual-tours/{tour['id']}/quality-report", headers=mgr_headers)
    assert qr_res.status_code == 200
    scan_status = qr_res.json()["data"]["report_data"].get("scan_status") or {}
    assert scan_status.get("validated_count", 0) >= 1

    # Record public analytics dollhouse_open & floorplan_open and verify summary increments
    ev1 = client.post(
        f"/api/v1/public/virtual-tours/{tour['id']}/analytics",
        json={"event_type": "dollhouse_open", "session_key": "p2-test-sess", "device_type": "desktop", "duration_sec": 12},
    )
    assert ev1.status_code == 201
    ev2 = client.post(
        f"/api/v1/public/virtual-tours/{tour['id']}/analytics",
        json={"event_type": "floorplan_open", "session_key": "p2-test-sess", "device_type": "desktop", "duration_sec": 9},
    )
    assert ev2.status_code == 201

    analytics_res = client.get(f"/api/v1/virtual-tours/{tour['id']}/analytics", headers=mgr_headers)
    assert analytics_res.status_code == 200
    an = analytics_res.json()["data"]
    assert an["dollhouse_opens"] >= 2
    assert an["floorplan_opens"] >= 2


def test_p2_scan_upload_processing_formats_and_rbac_security():
    client = TestClient(app)
    mgr = _login(client, "09121111111", "Manager@12345")
    mgr_headers = _agency_headers(mgr)
    agency_b = _login(client, "09123333333", "Manager@12345")
    b_headers = _agency_headers(agency_b)

    prop = _create_draft_property(client, mgr_headers, uuid.uuid4().hex[:6])
    tour = client.post(
        f"/api/v1/properties/{prop['id']}/virtual-tour",
        headers=mgr_headers,
        json={"title": "تور اسکن سه‌بعدی تست", "create_default_floor": True},
    ).json()["data"]
    tour_id = tour["id"]
    floor_id = tour["floors"][0]["id"]

    # Reject invalid extension / SVG
    bad_ext = client.post(
        f"/api/v1/virtual-tours/{tour_id}/scans",
        headers=mgr_headers,
        data={"source_device": "lidar_ios"},
        files={"file": ("malware.svg", b"<svg></svg>", "image/svg+xml")},
    )
    assert bad_ext.status_code == 400

    # Reject empty / malformed PLY
    bad_ply = client.post(
        f"/api/v1/virtual-tours/{tour_id}/scans",
        headers=mgr_headers,
        data={"source_device": "lidar_ios"},
        files={"file": ("corrupt.ply", b"not a ply header", "application/octet-stream")},
    )
    assert bad_ply.status_code == 400

    # 1. Upload & process PLY (with outliers)
    ply_up = client.post(
        f"/api/v1/virtual-tours/{tour_id}/scans",
        headers=mgr_headers,
        data={"source_device": "lidar_ios", "floor_id": floor_id},
        files={"file": ("room.ply", _make_room_ascii_ply(), "application/octet-stream")},
    )
    assert ply_up.status_code == 201, ply_up.text
    ply_scan_id = ply_up.json()["data"]["id"]

    proc_res = client.post(f"/api/v1/scans/{ply_scan_id}/process", headers=mgr_headers)
    assert proc_res.status_code == 202, proc_res.text
    assert proc_res.json()["data"]["job"]["job_type"] == "scan_process"
    assert proc_res.json()["data"]["job"]["state"] == "succeeded"

    ply_detail = client.get(f"/api/v1/scans/{ply_scan_id}", headers=mgr_headers).json()["data"]
    assert ply_detail["status"] == "validated"
    assert ply_detail["points_count"] > 200
    assert ply_detail["processing_result"]["outlier_points_count"] >= 2
    assert ply_detail["processing_result"]["point_density_per_sqm"] > 0
    assert ply_detail["bounding_box"]["dimensions_m"]["width"] == pytest.approx(5.0, abs=0.2)

    # Signed private streams return valid binaries; unsigned requests MUST return 403
    for key in ("raw_file_url", "preview_glb_url", "density_map_url"):
        signed_url = ply_detail[key]
        assert signed_url
        ok_stream = client.get(signed_url)
        assert ok_stream.status_code == 200
        if key == "preview_glb_url":
            assert ok_stream.content[:4] == b"glTF"
        elif key == "density_map_url":
            assert ok_stream.content[:8] == b"\x89PNG\r\n\x1a\n"

        unsigned_url = signed_url.split("?")[0]
        assert client.get(unsigned_url).status_code == 403
        assert client.get(unsigned_url, headers=b_headers).status_code == 403

    # Cross-agency access & delete MUST fail 403
    assert client.get(f"/api/v1/scans/{ply_scan_id}", headers=b_headers).status_code == 403
    assert client.post(f"/api/v1/scans/{ply_scan_id}/process", headers=b_headers).status_code == 403
    assert client.delete(f"/api/v1/scans/{ply_scan_id}", headers=b_headers).status_code == 403

    # 2. Upload & process uint16 Depth PNG
    depth_up = client.post(
        f"/api/v1/virtual-tours/{tour_id}/scans",
        headers=mgr_headers,
        data={"source_device": "depth_android"},
        files={"file": ("arcore-depth.png", _make_uint16_depth_png(), "image/png")},
    )
    assert depth_up.status_code == 201, depth_up.text
    depth_scan_id = depth_up.json()["data"]["id"]
    assert client.post(f"/api/v1/scans/{depth_scan_id}/process", headers=mgr_headers).status_code == 202
    depth_detail = client.get(f"/api/v1/scans/{depth_scan_id}", headers=mgr_headers).json()["data"]
    assert depth_detail["status"] == "validated"
    assert depth_detail["points_count"] > 100
    assert depth_detail["preview_glb_url"] is not None

    # 3. Upload & process Wavefront OBJ + XYZ point cloud
    obj_up = client.post(
        f"/api/v1/virtual-tours/{tour_id}/scans",
        headers=mgr_headers,
        data={"source_device": "photogrammetry"},
        files={"file": ("mesh.obj", _make_wavefront_obj_box(), "text/plain")},
    )
    assert obj_up.status_code == 201
    obj_id = obj_up.json()["data"]["id"]
    assert client.post(f"/api/v1/scans/{obj_id}/process", headers=mgr_headers).status_code == 202
    assert client.get(f"/api/v1/scans/{obj_id}", headers=mgr_headers).json()["data"]["status"] == "validated"

    xyz_bytes = "\n".join(f"{x * 0.5} {0.0 if y == 0 else 2.8} {z * 0.5}" for x in range(8) for z in range(6) for y in (0, 1)).encode("utf-8")
    xyz_up = client.post(
        f"/api/v1/virtual-tours/{tour_id}/scans",
        headers=mgr_headers,
        data={"source_device": "laser_scanner"},
        files={"file": ("cloud.xyz", xyz_bytes, "text/plain")},
    )
    assert xyz_up.status_code == 201
    xyz_id = xyz_up.json()["data"]["id"]
    assert client.post(f"/api/v1/scans/{xyz_id}/process", headers=mgr_headers).status_code == 202
    assert client.get(f"/api/v1/scans/{xyz_id}", headers=mgr_headers).json()["data"]["status"] == "validated"

    # List & Delete
    scans_list = client.get(f"/api/v1/virtual-tours/{tour_id}/scans", headers=mgr_headers).json()["data"]
    assert len(scans_list) == 4
    del_res = client.delete(f"/api/v1/scans/{xyz_id}", headers=mgr_headers)
    assert del_res.status_code == 200
    scans_after = client.get(f"/api/v1/virtual-tours/{tour_id}/scans", headers=mgr_headers).json()["data"]
    assert len(scans_after) == 3
