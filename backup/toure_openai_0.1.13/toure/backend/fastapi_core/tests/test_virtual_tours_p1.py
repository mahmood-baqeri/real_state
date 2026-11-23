import io
import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

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


def _make_floorplan_png(width: int = 800, height: int = 600) -> bytes:
    im = Image.new("RGB", (width, height), (250, 250, 252))
    draw = ImageDraw.Draw(im)
    draw.rectangle([80, 80, 720, 520], outline=(15, 118, 110), width=4)
    draw.line([420, 80, 420, 520], fill=(15, 23, 42), width=3)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _create_draft_property(client: TestClient, headers: dict, suffix: str) -> dict:
    res = client.post(
        "/api/v1/properties",
        headers=headers,
        json={
            "property_code": f"P1VT-{suffix}",
            "title": f"پنت‌هاوس دوبلکس پلان {suffix}",
            "property_type_id": "APARTMENT",
            "deal_type_id": "SALE",
            "visibility": "PRIVATE_AGENCY",
            "built_area_sqm": "220",
            "bedrooms": 3,
            "bathrooms": 2,
            "total_price": "38000000000",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["data"]


def test_p1_seeded_demo_dollhouse_glb_and_floorplan_public():
    client = TestClient(app)
    pub_props = client.get("/api/v1/properties/public?page=1&page_size=20")
    assert pub_props.status_code == 200
    demo_prop = next((p for p in pub_props.json()["data"] if p.get("property_code") == "PN-1001"), None)
    assert demo_prop is not None

    vt = client.get(f"/api/v1/public/properties/{demo_prop['id']}/virtual-tour").json()["data"]
    assert len(vt.get("floorplans") or []) >= 1
    assert len(vt.get("rooms") or []) >= 2
    assert vt.get("dollhouse") is not None
    assert vt["dollhouse"]["format"] == "glb"
    assert vt["dollhouse"]["geometry_source"] == "floorplan_2d_extrusion"

    glb_res = client.get(vt["dollhouse"]["file_url"])
    assert glb_res.status_code == 200
    assert glb_res.content[:4] == b"glTF"

    fp_res = client.get(vt["floorplans"][0]["file_url"])
    assert fp_res.status_code == 200
    assert len(fp_res.content) > 500


def test_p1_floorplan_calibration_rooms_walls_openings_and_glb_pipeline():
    client = TestClient(app)
    mgr = _login(client, "09121111111", "Manager@12345")
    mgr_headers = _agency_headers(mgr)
    agent = _login(client, "09122222222", "Agent@12345")
    agent_headers = _agency_headers(agent)
    agency_b = _login(client, "09123333333", "Manager@12345")
    b_headers = _agency_headers(agency_b)

    prop = _create_draft_property(client, mgr_headers, uuid.uuid4().hex[:6])
    tour_res = client.post(
        f"/api/v1/properties/{prop['id']}/virtual-tour",
        headers=mgr_headers,
        json={"title": "تور دوبلکس پلان و مدل", "create_default_floor": True},
    )
    assert tour_res.status_code == 201
    tour = tour_res.json()["data"]
    tour_id = tour["id"]
    floor_id = tour["floors"][0]["id"]

    # Create a scene to bind room -> 360 scene
    sc_res = client.post(
        f"/api/v1/virtual-tours/{tour_id}/scenes",
        headers=mgr_headers,
        json={"floor_id": floor_id, "title": "پذیرایی اصلی", "room_type": "living_room"},
    )
    assert sc_res.status_code == 201
    scene_id = sc_res.json()["data"]["id"]

    # Upload SVG rejected
    svg_res = client.post(
        f"/api/v1/virtual-tours/{tour_id}/floorplans",
        headers=mgr_headers,
        data={"floor_id": floor_id},
        files={"file": ("bad.svg", b"<svg></svg>", "image/svg+xml")},
    )
    assert svg_res.status_code == 400

    # Upload PNG floorplan
    png_res = client.post(
        f"/api/v1/virtual-tours/{tour_id}/floorplans",
        headers=mgr_headers,
        data={"floor_id": floor_id},
        files={"file": ("plan.png", _make_floorplan_png(), "image/png")},
    )
    assert png_res.status_code == 201, png_res.text
    fp = png_res.json()["data"]
    assert fp["width_px"] == 800

    # Upload PDF floorplan (also supported with generated preview raster)
    pdf_res = client.post(
        f"/api/v1/virtual-tours/{tour_id}/floorplans",
        headers=mgr_headers,
        data={"floor_id": floor_id},
        files={"file": ("plan.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n", "application/pdf")},
    )
    assert pdf_res.status_code == 201, pdf_res.text
    pdf_fp = pdf_res.json()["data"]
    assert pdf_fp["file_type"] == "pdf"

    # Re-upload PNG so active plan is crisp PNG & calibrate 400px -> 8.0m => 0.02 m/px
    png_res2 = client.post(
        f"/api/v1/virtual-tours/{tour_id}/floorplans",
        headers=mgr_headers,
        data={"floor_id": floor_id},
        files={"file": ("plan-v2.png", _make_floorplan_png(), "image/png")},
    )
    assert png_res2.status_code == 201
    active_fp_id = png_res2.json()["data"]["id"]

    cal_res = client.post(
        f"/api/v1/floorplans/{active_fp_id}/calibrate",
        headers=mgr_headers,
        json={"point_a": [100, 100], "point_b": [500, 100], "real_distance_m": 8.0},
    )
    assert cal_res.status_code == 200, cal_res.text
    assert abs(cal_res.json()["data"]["scale_m_per_px"] - 0.02) < 1e-5

    # Cross-agency calibration blocked
    assert (
        client.post(
            f"/api/v1/floorplans/{active_fp_id}/calibrate",
            headers=b_headers,
            json={"point_a": [0, 0], "point_b": [100, 0], "real_distance_m": 2.0},
        ).status_code
        == 403
    )

    # Create L-shaped room polygon (6x5 minus 2x2 corner = 26.00 sqm) bound to scene_id
    l_poly = [[0, 0], [6, 0], [6, 3], [4, 3], [4, 5], [0, 5]]
    rm_res = client.post(
        f"/api/v1/virtual-tours/{tour_id}/rooms",
        headers=mgr_headers,
        json={
            "floor_id": floor_id,
            "scene_id": scene_id,
            "floorplan_id": active_fp_id,
            "label": "پذیرایی L شکل",
            "room_type": "living_room",
            "polygon_points": l_poly,
            "height_m": 3.0,
        },
    )
    assert rm_res.status_code == 201, rm_res.text
    rm = rm_res.json()["data"]
    assert float(rm["area_sqm"]) == pytest.approx(26.0, abs=0.01)

    # Verify scene dimensions & geometry_source synced
    tour_after_room = client.get(f"/api/v1/virtual-tours/{tour_id}", headers=mgr_headers).json()["data"]
    scene_obj = next(s for s in tour_after_room["scenes"] if s["id"] == scene_id)
    assert scene_obj["geometry_source"] == "floorplan_2d"
    assert float(scene_obj["width_m"]) == pytest.approx(6.0, abs=0.01)
    assert float(scene_obj["length_m"]) == pytest.approx(5.0, abs=0.01)

    # Create measurement
    meas_res = client.post(
        f"/api/v1/rooms/{rm['id']}/measurements",
        headers=mgr_headers,
        json={"label": "طول دیوار شمالی", "start_point": [0, 0], "end_point": [6, 0]},
    )
    assert meas_res.status_code == 201
    assert float(meas_res.json()["data"]["distance_m"]) == pytest.approx(6.0, abs=0.01)

    # Create explicit wall segment + window & door openings
    w1_res = client.post(
        f"/api/v1/virtual-tours/{tour_id}/walls",
        headers=mgr_headers,
        json={
            "floor_id": floor_id,
            "floorplan_id": active_fp_id,
            "start_x": 0.0,
            "start_y": 0.0,
            "end_x": 6.0,
            "end_y": 0.0,
            "thickness_m": 0.20,
            "height_m": 3.0,
            "is_exterior": True,
        },
    )
    assert w1_res.status_code == 201
    wall_id = w1_res.json()["data"]["id"]

    op_res = client.post(
        f"/api/v1/walls/{wall_id}/openings",
        headers=mgr_headers,
        json={"kind": "window", "offset_ratio": 0.5, "width_m": 2.2, "height_m": 1.6, "sill_height_m": 0.8},
    )
    assert op_res.status_code == 201

    # Generate 3D Dollhouse GLB
    gen_res = client.post(
        f"/api/v1/virtual-tours/{tour_id}/generate-3d",
        headers=mgr_headers,
        json={"wall_height_m": 3.0, "wall_thickness_m": 0.18},
    )
    assert gen_res.status_code == 202, gen_res.text
    assert gen_res.json()["data"]["job"]["state"] == "succeeded"

    curr_res = client.get(f"/api/v1/virtual-tours/{tour_id}/model/current", headers=mgr_headers)
    assert curr_res.status_code == 200
    m1 = curr_res.json()["data"]
    assert m1 is not None
    assert m1["version"] == 1
    assert m1["format"] == "glb"
    assert m1["geometry_source"] == "floorplan_2d_extrusion"
    assert "تقریبی" in m1["estimated_accuracy"]
    assert float(m1["total_area_sqm"]) == pytest.approx(26.0, abs=0.01)

    # Download GLB binary & check glTF magic header; anonymous request without token MUST be 403 on unpublished tour
    glb_auth = client.get(m1["file_url"])
    assert glb_auth.status_code == 200
    assert glb_auth.content[:4] == b"glTF"

    base_glb_url = m1["file_url"].split("?")[0]
    assert client.get(base_glb_url).status_code == 403

    # Agent cannot approve 3D model (403); Manager approves (200)
    assert client.post(f"/api/v1/models/{m1['id']}/approve", headers=agent_headers).status_code == 403
    assert client.post(f"/api/v1/models/{m1['id']}/approve", headers=mgr_headers).status_code == 200

    # Generate v2, then restore v1 cleanly
    gen2 = client.post(f"/api/v1/virtual-tours/{tour_id}/generate-3d", headers=mgr_headers, json={})
    assert gen2.status_code == 202
    models_list = client.get(f"/api/v1/virtual-tours/{tour_id}/models", headers=mgr_headers).json()["data"]
    assert len(models_list) == 2

    rst = client.post(f"/api/v1/models/{m1['id']}/restore", headers=mgr_headers)
    assert rst.status_code == 200
    assert rst.json()["data"]["is_current"] is True
