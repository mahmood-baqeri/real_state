import io
import os
import sys
import uuid
from pathlib import Path

import cv2
import numpy as np
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


def _make_textured_jpeg(width: int = 800, height: int = 600, seed_idx: int = 0) -> bytes:
    """Generates a sharp, high-contrast architectural-style JPEG frame with distinct features per yaw index."""
    img = Image.new("RGB", (width, height), (210 - seed_idx * 10, 215, 222))
    draw = ImageDraw.Draw(img)
    # Horizon wall/floor split
    draw.rectangle([0, int(height * 0.62), width, height], fill=(140, 118, 96))
    # Window / door frames shifted horizontally to create overlapping features across yaws
    shift = (seed_idx * 60) % (width // 2)
    draw.rectangle([80 + shift, 90, 260 + shift, 340], fill=(165, 208, 240), outline=(45, 55, 72), width=6)
    draw.line([170 + shift, 90, 170 + shift, 340], fill=(45, 55, 72), width=4)
    draw.line([80 + shift, 215, 260 + shift, 215], fill=(45, 55, 72), width=4)
    # Fine grid/tiles on floor & wall corners for sharp Laplacian texture
    for x in range(40, width - 40, 48):
        draw.line([x, int(height * 0.62), x + 20, height], fill=(95, 80, 66), width=2)
    for y in range(60, int(height * 0.6), 40):
        draw.rectangle([width - 140 + (seed_idx * 8), y, width - 70 + (seed_idx * 8), y + 22], fill=(70, 95, 130))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _make_dark_blurry_jpeg(width: int = 640, height: int = 480) -> bytes:
    arr = np.full((height, width, 3), 8, dtype=np.uint8)
    ok, enc = cv2.imencode(".jpg", arr)
    assert ok
    return enc.tobytes()


def _make_equirectangular_jpeg(width: int = 1600, height: int = 800) -> bytes:
    return _make_textured_jpeg(width=width, height=height, seed_idx=3)


def _create_draft_property(client: TestClient, headers: dict, suffix: str) -> dict:
    res = client.post(
        "/api/v1/properties",
        headers=headers,
        json={
            "property_code": f"VT-{suffix}",
            "title": f"آپارتمان تور مجازی {suffix}",
            "property_type_id": "APARTMENT",
            "deal_type_id": "SALE",
            "visibility": "PRIVATE_AGENCY",
            "built_area_sqm": "165",
            "bedrooms": 3,
            "bathrooms": 2,
            "total_price": "28500000000",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["data"]


def test_p0_seeded_demo_tour_is_published_and_streamable():
    client = TestClient(app)
    pub_props = client.get("/api/v1/properties/public?page=1&page_size=20")
    assert pub_props.status_code == 200
    items = pub_props.json()["data"]
    demo_prop = next((p for p in items if p.get("property_code") == "PN-1001"), None)
    assert demo_prop is not None
    assert demo_prop["has_virtual_tour"] is True
    assert demo_prop["virtual_tour_id"] is not None

    vt_res = client.get(f"/api/v1/public/properties/{demo_prop['id']}/virtual-tour")
    assert vt_res.status_code == 200, vt_res.text
    vt_data = vt_res.json()["data"]
    assert len(vt_data["scenes"]) >= 2
    assert len(vt_data["floors"]) >= 1
    # A published tour must also be reachable through its standalone share slug.
    slug_res = client.get(f"/api/v1/public/virtual-tours/{vt_data['public_slug']}")
    assert slug_res.status_code == 200, slug_res.text
    assert slug_res.json()["data"]["tour_id"] == vt_data["tour_id"]
    assert slug_res.json()["data"]["public_slug"] == vt_data["public_slug"]

    pano_url = vt_data["scenes"][0]["panorama_url"]
    thumb_url = vt_data["scenes"][0]["thumbnail_url"]
    assert pano_url and thumb_url
    pano_bin = client.get(pano_url)
    assert pano_bin.status_code == 200
    assert pano_bin.headers["content-type"].startswith("image/jpeg")
    assert len(pano_bin.content) > 5000

    thumb_bin = client.get(thumb_url)
    assert thumb_bin.status_code == 200
    assert thumb_bin.headers["content-type"].startswith("image/jpeg")


def test_p0_full_lifecycle_capture_opencv_stitch_review_links_publish_and_security():
    client = TestClient(app)
    suffix = uuid.uuid4().hex[:6].upper()

    mgr_a = _login(client, "09121111111", "Manager@12345")
    mgr_b = _login(client, "09123333333", "Manager@12345")
    agent_a = _login(client, "09122222222", "Agent@12345")
    customer = _login(client, "09124444444", "Customer@12345")

    hdr_a = _agency_headers(mgr_a)
    hdr_b = _agency_headers(mgr_b)
    hdr_agent = _agency_headers(agent_a)
    hdr_cust = {"Authorization": f"Bearer {customer['access']}"}

    prop = _create_draft_property(client, hdr_a, suffix)
    prop_id = prop["id"]

    # Property initially has no active tour
    empty_vt = client.get(f"/api/v1/properties/{prop_id}/virtual-tour", headers=hdr_a)
    assert empty_vt.status_code == 200
    assert empty_vt.json()["data"]["tour"] is None
    assert len(empty_vt.json()["data"]["config"]["room_types"]) >= 8

    # Customer cannot create or access internal tour
    cust_create = client.post(
        f"/api/v1/properties/{prop_id}/virtual-tour",
        headers=hdr_cust,
        json={"title": "تور غیرمجاز"},
    )
    assert cust_create.status_code == 403

    # Create tour + verify conflict on second active tour + archive + recreate
    c1 = client.post(
        f"/api/v1/properties/{prop_id}/virtual-tour",
        headers=hdr_a,
        json={"title": f"تور {suffix}", "description": "تور آزمایشی P0"},
    )
    assert c1.status_code == 201, c1.text
    first_tour_id = c1.json()["data"]["id"]

    c_dup = client.post(
        f"/api/v1/properties/{prop_id}/virtual-tour",
        headers=hdr_a,
        json={"title": "دومین تور فعال"},
    )
    assert c_dup.status_code == 409

    arch = client.delete(f"/api/v1/virtual-tours/{first_tour_id}", headers=hdr_a)
    assert arch.status_code == 200
    assert arch.json()["data"]["status"] == "archived"

    c2 = client.post(
        f"/api/v1/properties/{prop_id}/virtual-tour",
        headers=hdr_a,
        json={"title": f"تور اصلی {suffix}", "create_default_floor": True},
    )
    assert c2.status_code == 201
    tour = c2.json()["data"]
    tour_id = tour["id"]
    floor_id = tour["floors"][0]["id"]

    # Tenant isolation: mgr_b cannot view or mutate Agency A tour
    assert client.get(f"/api/v1/virtual-tours/{tour_id}", headers=hdr_b).status_code == 403
    assert (
        client.post(
            f"/api/v1/virtual-tours/{tour_id}/floors",
            headers=hdr_b,
            json={"title": "طبقه نفوذی", "order": 1, "elevation_m": 3},
        ).status_code
        == 403
    )

    # Create Floor 2 and two Scenes
    f2_res = client.post(
        f"/api/v1/virtual-tours/{tour_id}/floors",
        headers=hdr_a,
        json={"title": "طبقه اول", "order": 1, "elevation_m": 3.2},
    )
    assert f2_res.status_code == 201

    # Empty scene title rejected; unknown room_type normalized to "other" and cleanable via DELETE
    bad_scene = client.post(
        f"/api/v1/virtual-tours/{tour_id}/scenes",
        headers=hdr_a,
        json={"floor_id": floor_id, "title": "   ", "room_type": "living_room"},
    )
    assert bad_scene.status_code == 400
    norm_scene = client.post(
        f"/api/v1/virtual-tours/{tour_id}/scenes",
        headers=hdr_a,
        json={"floor_id": floor_id, "title": "انباری موقت", "room_type": "spaceship"},
    )
    assert norm_scene.status_code == 201
    assert norm_scene.json()["data"]["room_type"] == "other"
    assert client.delete(f"/api/v1/scenes/{norm_scene.json()['data']['id']}", headers=hdr_a).status_code == 200

    sc1_res = client.post(
        f"/api/v1/virtual-tours/{tour_id}/scenes",
        headers=hdr_a,
        json={
            "floor_id": floor_id,
            "title": "پذیرایی",
            "room_type": "living_room",
            "is_start_scene": True,
            "initial_yaw": 15.0,
        },
    )
    assert sc1_res.status_code == 201, sc1_res.text
    sc1_id = sc1_res.json()["data"]["id"]

    sc2_res = client.post(
        f"/api/v1/virtual-tours/{tour_id}/scenes",
        headers=hdr_a,
        json={
            "floor_id": floor_id,
            "title": "آشپزخانه",
            "room_type": "kitchen",
            "is_start_scene": False,
        },
    )
    assert sc2_res.status_code == 201
    sc2_id = sc2_res.json()["data"]["id"]

    # Guided Capture Session (14 steps) on Scene 1
    cap_res = client.post(
        f"/api/v1/scenes/{sc1_id}/capture-sessions",
        headers=hdr_agent,
        json={"device_info": {"model": "TestPhone", "os": "Android"}, "allow_partial_stitch": True},
    )
    assert cap_res.status_code == 201, cap_res.text
    sess = cap_res.json()["data"]
    sess_id = sess["id"]
    assert len(sess["steps"]) >= 12

    # Invalid SVG upload rejected cleanly
    svg_up = client.post(
        f"/api/v1/capture-sessions/{sess_id}/images",
        headers=hdr_agent,
        data={"sequence": "1", "yaw": "0", "pitch": "0"},
        files={"file": ("evil.svg", b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", "image/svg+xml")},
    )
    assert svg_up.status_code == 400

    # Upload dark/blurry frame -> QC marks rejected
    dark_up = client.post(
        f"/api/v1/capture-sessions/{sess_id}/images",
        headers=hdr_agent,
        data={"sequence": "1", "yaw": "0", "pitch": "0"},
        files={"file": ("dark.jpg", _make_dark_blurry_jpeg(), "image/jpeg")},
    )
    assert dark_up.status_code == 201
    assert dark_up.json()["data"]["image"]["status"] == "rejected"

    # Retake seq 1..4 with crisp textured JPEGs
    uploaded_img_ids = []
    for idx in range(1, 5):
        up = client.post(
            f"/api/v1/capture-sessions/{sess_id}/images",
            headers=hdr_agent,
            data={"sequence": str(idx), "yaw": str((idx - 1) * 30), "pitch": "0"},
            files={"file": (f"frame_{idx}.jpg", _make_textured_jpeg(seed_idx=idx), "image/jpeg")},
        )
        assert up.status_code == 201, up.text
        img_obj = up.json()["data"]["image"]
        assert img_obj["status"] in ("passed", "warning")
        assert img_obj["analysis"]["blur_score"] > 10
        uploaded_img_ids.append(img_obj["id"])

    # Raw capture image MUST NEVER be accessible anonymously without signed token
    raw_anon = client.get(f"/api/v1/virtual-tours/files/capture/{uploaded_img_ids[0]}")
    assert raw_anon.status_code == 403

    # مراحل افقی و حلقهٔ فوقانی در الگوی فعلی اجباری هستند.
    assert client.post(f"/api/v1/capture-sessions/{sess_id}/steps/5/skip", headers=hdr_agent).status_code == 400
    assert client.post(f"/api/v1/capture-sessions/{sess_id}/steps/13/skip", headers=hdr_agent).status_code == 400

    comp = client.post(f"/api/v1/capture-sessions/{sess_id}/complete", headers=hdr_agent)
    assert comp.status_code == 200

    # Enqueue real OpenCV stitch with Idempotency-Key
    idem = f"stitch-{uuid.uuid4().hex[:8]}"
    proc1 = client.post(
        f"/api/v1/scenes/{sc1_id}/process",
        headers={**hdr_agent, "Idempotency-Key": idem},
        json={"session_id": sess_id, "reprocess": False},
    )
    assert proc1.status_code == 202, proc1.text
    job1 = proc1.json()["data"]
    assert job1["state"] == "succeeded"
    assert job1["progress"] == 100

    proc_dup = client.post(
        f"/api/v1/scenes/{sc1_id}/process",
        headers={**hdr_agent, "Idempotency-Key": idem},
        json={"session_id": sess_id, "reprocess": False},
    )
    assert proc_dup.status_code == 202
    assert proc_dup.json()["data"]["id"] == job1["id"]

    # Check created PanoramaVersion v1 is valid 2:1 equirectangular JPEG
    panos_res = client.get(f"/api/v1/scenes/{sc1_id}/panoramas", headers=hdr_a)
    assert panos_res.status_code == 200
    panos = panos_res.json()["data"]
    assert len(panos) == 1
    p1 = panos[0]
    assert p1["state"] == "review"
    assert p1["width_px"] == 2 * p1["height_px"]

    # Agent cannot approve panorama
    assert client.post(f"/api/v1/scenes/{sc1_id}/approve-panorama", headers=hdr_agent).status_code == 403

    # Direct upload v2, approve v2, then reject -> or restore v1
    direct_up = client.post(
        f"/api/v1/scenes/{sc1_id}/panoramas/upload",
        headers=hdr_a,
        files={"file": ("pano360.jpg", _make_equirectangular_jpeg(), "image/jpeg")},
    )
    assert direct_up.status_code == 201, direct_up.text
    p2_id = direct_up.json()["data"]["id"]
    assert direct_up.json()["data"]["version"] == 2

    # Approve v2 as manager
    app_res = client.post(
        f"/api/v1/scenes/{sc1_id}/approve-panorama",
        headers=hdr_a,
        json={"panorama_version_id": p2_id},
    )
    assert app_res.status_code == 200
    assert app_res.json()["data"]["state"] == "approved"

    # نسخهٔ دوخته‌شدهٔ این سناریو پوشش ناقص دارد و قابل بازیابی نیست.
    rejected_restore = client.post(f"/api/v1/scenes/{sc1_id}/panoramas/{p1['id']}/restore", headers=hdr_a)
    assert rejected_restore.status_code == 400, rejected_restore.text

    # جابه‌جایی از نسخهٔ تأییدشدهٔ سوم به دوم تاریخچه را حفظ می‌کند.
    replacement = client.post(
        f"/api/v1/scenes/{sc1_id}/panoramas/upload",
        headers=hdr_a,
        files={"file": ("replacement360.jpg", _make_equirectangular_jpeg(), "image/jpeg")},
    )
    assert replacement.status_code == 201, replacement.text
    p3_id = replacement.json()["data"]["id"]
    app_v3 = client.post(
        f"/api/v1/scenes/{sc1_id}/approve-panorama",
        headers=hdr_a,
        json={"panorama_version_id": p3_id},
    )
    assert app_v3.status_code == 200, app_v3.text
    rest_res = client.post(f"/api/v1/scenes/{sc1_id}/panoramas/{p2_id}/restore", headers=hdr_a)
    assert rest_res.status_code == 200, rest_res.text
    assert rest_res.json()["data"]["is_current"] is True

    # Scene 2 still has no panorama -> publish MUST fail quality gate
    qr_fail = client.get(f"/api/v1/virtual-tours/{tour_id}/quality-report", headers=hdr_a)
    assert qr_fail.status_code == 200
    assert qr_fail.json()["data"]["is_ready_to_publish"] is False
    pub_blocked = client.post(f"/api/v1/virtual-tours/{tour_id}/publish", headers=hdr_a)
    assert pub_blocked.status_code == 400

    # Upload direct panorama for Scene 2 and approve it
    sc2_up = client.post(
        f"/api/v1/scenes/{sc2_id}/panoramas/upload",
        headers=hdr_a,
        files={"file": ("kitchen360.jpg", _make_equirectangular_jpeg(), "image/jpeg")},
    )
    assert sc2_up.status_code == 201
    assert client.post(f"/api/v1/scenes/{sc2_id}/approve-panorama", headers=hdr_a).status_code == 200

    # Create bidirectional SceneLink + Hotspot; cross-tour link must fail
    lnk_res = client.post(
        f"/api/v1/virtual-tours/{tour_id}/links",
        headers=hdr_a,
        json={
            "source_scene_id": sc1_id,
            "target_scene_id": sc2_id,
            "yaw": 45.0,
            "pitch": -4.0,
            "title": "ورود به آشپزخانه",
            "bidirectional": True,
        },
    )
    assert lnk_res.status_code == 201, lnk_res.text
    all_links = client.get(f"/api/v1/virtual-tours/{tour_id}/links", headers=hdr_a).json()["data"]
    assert len(all_links) == 2

    hs_res = client.post(
        f"/api/v1/scenes/{sc1_id}/hotspots",
        headers=hdr_a,
        json={
            "kind": "info",
            "title": "سنگ اسلب طبیعی",
            "body": "سنگ دهبید سوپر",
            "yaw": 120.0,
            "pitch": -10.0,
        },
    )
    assert hs_res.status_code == 201
    hs_id = hs_res.json()["data"]["id"]

    # Agent cannot publish tour; Manager publishes tour
    assert client.post(f"/api/v1/virtual-tours/{tour_id}/publish", headers=hdr_agent).status_code == 403
    pub_ok = client.post(f"/api/v1/virtual-tours/{tour_id}/publish", headers=hdr_a)
    assert pub_ok.status_code == 200, pub_ok.text
    assert pub_ok.json()["data"]["version"] == 1

    # Draft/private property MUST NOT expose virtual tour publicly even though tour is published!
    priv_pub_res = client.get(f"/api/v1/public/properties/{prop_id}/virtual-tour")
    assert priv_pub_res.status_code == 404
    assert client.get(f"/api/v1/virtual-tours/files/panorama/{p1['id']}").status_code == 403

    # Verify + make property PUBLIC_PORTAL + PUBLISH property
    assert (
        client.patch(
            f"/api/v1/properties/{prop_id}",
            headers=hdr_a,
            json={"visibility": "PUBLIC_PORTAL"},
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"/api/v1/properties/{prop_id}/verification",
            headers=hdr_a,
            json={
                "physical_verified": True,
                "deed_verified": True,
                "owner_consent_verified": True,
            },
        ).status_code
        == 200
    )
    assert client.post(f"/api/v1/properties/{prop_id}/publish", headers=hdr_a).status_code == 200

    # Now public virtual tour & anonymous panorama streaming succeed!
    public_vt = client.get(f"/api/v1/public/properties/{prop_id}/virtual-tour")
    assert public_vt.status_code == 200, public_vt.text
    pub_payload = public_vt.json()["data"]
    assert len(pub_payload["scenes"]) == 2
    assert client.get(f"/api/v1/virtual-tours/files/panorama/{p2_id}").status_code == 200
    assert client.get(f"/api/v1/virtual-tours/files/panorama/{p1['id']}").status_code == 403

    # Analytics event recording + dashboard summary
    ev1 = client.post(
        f"/api/v1/public/virtual-tours/{tour_id}/analytics",
        json={"event_type": "tour_open", "session_key": f"sess-{suffix}", "device_type": "desktop"},
    )
    assert ev1.status_code == 201
    ev2 = client.post(
        f"/api/v1/public/virtual-tours/{tour_id}/analytics",
        json={
            "event_type": "hotspot_click",
            "scene_id": sc1_id,
            "hotspot_id": hs_id,
            "session_key": f"sess-{suffix}",
            "device_type": "mobile",
            "duration_sec": 18,
        },
    )
    assert ev2.status_code == 201

    analytics_summary = client.get(f"/api/v1/virtual-tours/{tour_id}/analytics", headers=hdr_a)
    assert analytics_summary.status_code == 200
    adata = analytics_summary.json()["data"]
    assert adata["total_views"] >= 1
    assert adata["hotspot_clicks"] >= 1
    assert adata["avg_duration_seconds"] >= 1
    assert len(adata["device_breakdown"]) >= 1

    # Verify audit trail entries were recorded
    from apps.audit.models import AuditLog

    assert AuditLog.objects.filter(action__startswith="virtual_tour.", agency_id=prop["agency_id"]).count() >= 5

    # WebSocket job monitor smoke test
    ticket = client.post("/api/v1/auth/ws-ticket", headers=hdr_a)
    assert ticket.status_code == 200, ticket.text
    with client.websocket_connect(
        f"/api/v1/ws/virtual-tours/{tour_id}/jobs",
        subprotocols=["bonyan.auth", "ticket." + ticket.json()["data"]["ticket"]],
    ) as ws:
        msg = ws.receive_json()
        assert msg["event"] == "tour_jobs_snapshot"
        assert msg["data"]["tour_id"] == tour_id
