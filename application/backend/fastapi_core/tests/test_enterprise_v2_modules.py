import json
import os
import sys
import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import httpx
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


def test_1_hierarchical_geography_crud_validation_and_pagination():
    client = TestClient(app)
    super_admin = _login(client, "09120000001", "Admin@12345")
    admin_headers = {"Authorization": f"Bearer {super_admin['access']}"}

    # List seeded hierarchy
    provs = client.get("/api/v1/locations/provinces?page=1&page_size=20")
    assert provs.status_code == 200
    prov_items = provs.json()["data"]
    assert len(prov_items) >= 3
    tehran = next((p for p in prov_items if p["name_fa"] == "تهران"), prov_items[0])

    cities = client.get(f"/api/v1/locations/cities?province_id={tehran['id']}")
    assert cities.status_code == 200
    assert len(cities.json()["data"]) >= 1
    tehran_city = next((c for c in cities.json()["data"] if c["name_fa"] == "تهران"), cities.json()["data"][0])

    districts = client.get(f"/api/v1/locations/districts?city_id={tehran_city['id']}")
    assert districts.status_code == 200
    assert len(districts.json()["data"]) >= 1
    first_dist = districts.json()["data"][0]

    nbrs = client.get(f"/api/v1/locations/neighborhoods?district_id={first_dist['id']}")
    assert nbrs.status_code == 200
    assert len(nbrs.json()["data"]) >= 1

    # Customer / Agent cannot create geography node
    agent = _login(client, "09122222222", "Agent@12345")
    forbidden = client.post(
        "/api/v1/locations/provinces",
        headers=_agency_headers(agent),
        json={"name_fa": "استان غیرمجاز"},
    )
    assert forbidden.status_code == 403

    # Admin creates new province -> city -> district -> neighborhood and toggles inactive
    suffix = uuid.uuid4().hex[:6]
    p_res = client.post(
        "/api/v1/locations/provinces",
        headers=admin_headers,
        json={"name_fa": f"استان تست {suffix}", "name_en": f"TestProv-{suffix}"},
    )
    assert p_res.status_code == 201, p_res.text
    p_id = p_res.json()["data"]["id"]

    c_res = client.post(
        "/api/v1/locations/cities",
        headers=admin_headers,
        json={"province_id": p_id, "name_fa": f"شهر تست {suffix}"},
    )
    assert c_res.status_code == 201
    c_id = c_res.json()["data"]["id"]

    d_res = client.post(
        "/api/v1/locations/districts",
        headers=admin_headers,
        json={"city_id": c_id, "name_fa": f"منطقه تست {suffix}"},
    )
    assert d_res.status_code == 201
    d_id = d_res.json()["data"]["id"]

    n_res = client.post(
        "/api/v1/locations/neighborhoods",
        headers=admin_headers,
        json={"district_id": d_id, "name_fa": f"محله تست {suffix}"},
    )
    assert n_res.status_code == 201
    n_id = n_res.json()["data"]["id"]

    # Cross-hierarchy mismatch rejection on property creation
    manager = _login(client, "09121111111", "Manager@12345")
    mismatch = client.post(
        "/api/v1/properties",
        headers=_agency_headers(manager),
        json={
            "property_code": f"MIS-{suffix}",
            "title": "ملک با سلسله‌مراتب ناسازگار",
            "property_type_id": "APARTMENT",
            "deal_type_id": "SALE",
            "built_area_sqm": "100",
            "total_price": "10000000000",
            "location": {
                "province_id": tehran["id"],
                "city_id": c_id,  # belongs to TestProv, not Tehran!
            },
        },
    )
    assert mismatch.status_code == 400

    # Deactivating node hides it from active_only=true queries
    patch_res = client.patch(
        f"/api/v1/locations/neighborhood/{n_id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["is_active"] is False

    active_nbrs = client.get(f"/api/v1/locations/neighborhoods?district_id={d_id}&active_only=true")
    assert all(item["id"] != n_id for item in active_nbrs.json()["data"])


def test_2_and_3_spatial_map_search_and_categorized_amenities():
    client = TestClient(app)
    manager = _login(client, "09121111111", "Manager@12345")
    headers = _agency_headers(manager)

    # Check 7+ amenity categories and typed amenities
    cat_res = client.get("/api/v1/properties/catalog")
    assert cat_res.status_code == 200
    cat_data = cat_res.json()["data"]
    assert len(cat_data["amenity_categories"]) >= 7
    assert any(a["value_type"] != "BOOLEAN" for a in cat_data["amenities"])

    # Create category + custom typed amenity as super admin
    super_admin = _login(client, "09120000001", "Admin@12345")
    admin_headers = {"Authorization": f"Bearer {super_admin['access']}"}
    am_code = f"EV_SPOT_{uuid.uuid4().hex[:4].upper()}"
    am_res = client.post(
        "/api/v1/properties/amenities",
        headers=admin_headers,
        json={
            "code": am_code,
            "category_code": cat_data["amenity_categories"][0]["code"],
            "name_fa": "تعداد ایستگاه شارژ",
            "value_type": "INTEGER",
            "unit_label": "عدد",
            "is_active": True,
        },
    )
    assert am_res.status_code == 201

    # Fetch valid Tehran hierarchy
    tehran_city = next(
        c for c in client.get("/api/v1/locations/cities").json()["data"] if c["name_fa"] == "تهران"
    )
    tehran_dist = client.get(f"/api/v1/locations/districts?city_id={tehran_city['id']}").json()["data"][0]

    # Create & publish a property at exact coordinates inside polygon [35.79..35.82, 51.40..51.45]
    code = f"SP-{uuid.uuid4().hex[:6].upper()}"
    create_res = client.post(
        "/api/v1/properties",
        headers=headers,
        json={
            "property_code": code,
            "title": "پنت‌هاوس اختصاصی با نقشه و امکانات عددی",
            "property_type_id": "APARTMENT",
            "deal_type_id": "SALE",
            "built_area_sqm": "210",
            "bedrooms": 3,
            "total_price": "42000000000",
            "amenity_codes": ["PARKING", am_code],
            "amenity_values": [
                {"code": am_code, "value_number": 2, "value_text": "شارژ سریع"},
                {"code": "PARKING", "value_number": 2},
            ],
            "location": {
                "city_id": tehran_city["id"],
                "district_id": tehran_dist["id"],
                "latitude": "35.805123",
                "longitude": "51.425678",
                "hide_exact_address": True,
            },
        },
    )
    assert create_res.status_code == 201, create_res.text
    prop = create_res.json()["data"]
    assert any(a["code"] == am_code and a["value_number"] in ("2", "2.00") for a in prop["amenities"])

    # Unverified property must be blocked from public publishing
    blocked_pub = client.post(f"/api/v1/properties/{prop['id']}/publish", headers=headers)
    assert blocked_pub.status_code in (400, 422), blocked_pub.text

    ver_res = client.put(
        f"/api/v1/properties/{prop['id']}/verification",
        headers=headers,
        json={
            "physical_verified": True,
            "deed_verified": True,
            "owner_consent_verified": True,
            "physical_notes": "بازدید فیزیکی تایید شد",
        },
    )
    assert ver_res.status_code == 200, ver_res.text

    pub_res = client.post(f"/api/v1/properties/{prop['id']}/publish", headers=headers)
    assert pub_res.status_code == 200, pub_res.text

    # Spatial Bounding Box search
    bbox_res = client.get(
        "/api/v1/search/properties?min_lat=35.79&max_lat=35.82&min_lng=51.40&max_lng=51.45"
    )
    assert bbox_res.status_code == 200
    assert bbox_res.json()["meta"]["spatial_mode"] == "bounds"
    hit = next((x for x in bbox_res.json()["data"] if x["id"] == prop["id"]), None)
    assert hit is not None
    # Public precision masking enforced (quantized to 2 decimals)
    assert hit["latitude"] == "35.81"
    assert hit["longitude"] == "51.43"

    # Exact Polygon ray-casting search
    poly_inside = json.dumps([[35.79, 51.40], [35.82, 51.40], [35.82, 51.45], [35.79, 51.45]])
    poly_res = client.get(
        f"/api/v1/search/properties?polygon={poly_inside}&amenities={am_code}"
    )
    assert poly_res.status_code == 200
    assert poly_res.json()["meta"]["spatial_mode"] == "polygon"
    assert any(x["id"] == prop["id"] for x in poly_res.json()["data"])

    # Polygon completely outside should exclude the property
    poly_outside = json.dumps([[32.60, 51.60], [32.70, 51.60], [32.70, 51.70], [32.60, 51.70]])
    out_res = client.get(f"/api/v1/search/properties?polygon={poly_outside}")
    assert out_res.status_code == 200
    assert all(x["id"] != prop["id"] for x in out_res.json()["data"])


def test_4_secure_upload_validation_and_media_reorder():
    client = TestClient(app)
    manager = _login(client, "09121111111", "Manager@12345")
    headers = _agency_headers(manager)
    props = client.get("/api/v1/properties", headers=headers).json()["data"]
    assert len(props) >= 1
    prop_id = props[0]["id"]

    # Reject dangerous extension / spoofed MIME
    bad_exe = client.post(
        f"/api/v1/properties/{prop_id}/media/upload",
        headers=headers,
        files={"file": ("malware.exe", b"MZ\x90\x00evil", "application/octet-stream")},
    )
    assert bad_exe.status_code == 400

    bad_svg = client.post(
        f"/api/v1/properties/{prop_id}/media/upload",
        headers=headers,
        files={"file": ("xss.svg", b"<svg><script>alert(1)</script></svg>", "image/svg+xml")},
    )
    assert bad_svg.status_code == 400

    # Accept valid PNG magic-byte header
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    up1 = client.post(
        f"/api/v1/properties/{prop_id}/media/upload",
        headers=headers,
        data={"title": "نمای اول", "is_cover": "true"},
        files={"file": ("front.png", png_bytes, "image/png")},
    )
    assert up1.status_code == 201, up1.text
    up2 = client.post(
        f"/api/v1/properties/{prop_id}/media/upload",
        headers=headers,
        data={"title": "نمای دوم", "is_cover": "false"},
        files={"file": ("living.png", png_bytes, "image/png")},
    )
    assert up2.status_code == 201

    m1_id = up1.json()["data"]["id"]
    m2_id = up2.json()["data"]["id"]
    re_res = client.post(
        f"/api/v1/properties/{prop_id}/media/reorder",
        headers=headers,
        json={"ordered_media_ids": [m2_id, m1_id], "cover_media_id": m2_id},
    )
    assert re_res.status_code == 200
    re_items = re_res.json()["data"]
    m2 = next(x for x in re_items if x["id"] == m2_id)
    assert m2["is_cover"] is True


def test_5_gapgpt_ai_integration_retry_and_fallback():
    client = TestClient(app)
    manager = _login(client, "09121111111", "Manager@12345")
    headers = _agency_headers(manager)

    # Status endpoint
    st = client.get("/api/v1/ai/status", headers=headers)
    assert st.status_code == 200
    model_ids = [m["id"] if isinstance(m, dict) else m for m in st.json()["data"]["supported_models"]]
    assert "gpt-4o" in model_ids

    # Unconfigured fallback should succeed cleanly via resilient domain engine
    with patch("django.conf.settings.GAPGPT_API_KEY", ""):
        fb_res = client.post(
            "/api/v1/ai/assistant/chat",
            headers=headers,
            json={"message": "وضعیت کلی فایل‌ها و مذاکرات آژانس را خلاصه کن", "task_mode": "GENERAL"},
        )
        assert fb_res.status_code == 200, fb_res.text
        assert fb_res.json()["data"]["provider"] == "DOMAIN_ENGINE"
        assert len(fb_res.json()["data"]["reply"]) > 20

    # Mocked live GapGPT call with HTTP 429 exponential backoff retry -> success
    calls = {"count": 0}
    orig_post = httpx.Client.post

    def fake_post(self, url, *args, **kwargs):
        url_str = str(url)
        if "gapgpt.app" not in url_str:
            return orig_post(self, url, *args, **kwargs)
        calls["count"] += 1
        req = httpx.Request("POST", url_str)
        if calls["count"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0.01"}, json={"error": "rate_limit"}, request=req)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-gapgpt-test",
                "model": "gpt-5.6",
                "choices": [{"message": {"content": "تحلیل GapGPT: پیشنهاد تمرکز روی املاک زعفرانیه."}}],
                "usage": {"total_tokens": 142},
            },
            request=req,
        )

    with patch("django.conf.settings.GAPGPT_API_KEY", "sk-gapgpt-test-123456"), patch.object(
        httpx.Client, "post", fake_post
    ):
        ai_res = client.post(
            "/api/v1/ai/assistant/chat",
            headers=headers,
            json={
                "message": "پیشنهاد استراتژی فروش بده",
                "task_mode": "SALES_COACH",
                "model": "gpt-5.6",
            },
        )
        assert ai_res.status_code == 200, ai_res.text
        data = ai_res.json()["data"]
        assert data["provider"] == "GAPGPT"
        assert data["tokens_used"] == 142
        assert calls["count"] == 2


def test_6_enterprise_negotiation_workflow_offers_activities_analytics_and_contract():
    client = TestClient(app)
    manager = _login(client, "09121111111", "Manager@12345")
    headers = _agency_headers(manager)

    props = client.get("/api/v1/properties", headers=headers).json()["data"]
    custs = client.get("/api/v1/customers", headers=headers).json()["data"]
    assert len(props) >= 1 and len(custs) >= 1

    neg_create = client.post(
        "/api/v1/negotiations",
        headers=headers,
        json={
            "property_id": props[0]["id"],
            "customer_id": custs[0]["id"],
            "asking_price": "30000000000",
            "initial_price": "27000000000",
            "next_action": "تماس با مالک جهت ارائه پیشنهاد",
            "notes": "خریدار نقدی آماده عقد مبایعه‌نامه",
        },
    )
    assert neg_create.status_code == 201, neg_create.text
    neg = neg_create.json()["data"]
    neg_id = neg["id"]
    assert neg["status"] == "BUYER_OFFERED"
    assert len(neg["offers"]) == 1

    # Add seller counter offer
    off2 = client.post(
        f"/api/v1/negotiations/{neg_id}/offers",
        headers=headers,
        json={"offered_by": "SELLER", "proposed_price": "28800000000", "notes": "شرایط پرداخت ۲ مرحله‌ای"},
    )
    assert off2.status_code == 201
    assert off2.json()["data"]["version_number"] == 2

    # Log call activity
    act = client.post(
        f"/api/v1/negotiations/{neg_id}/activities",
        headers=headers,
        json={"activity_type": "CALL", "title": "تماس هماهنگی جلسه حضوری", "outcome": "تأیید ساعت ۱۸"},
    )
    assert act.status_code == 201

    # Transition to PRE_AGREEMENT and convert to Contract
    resp = client.post(
        f"/api/v1/negotiations/{neg_id}/respond",
        headers=headers,
        json={"status": "PRE_AGREEMENT", "agreed_price": "28500000000", "reason": "توافق نهایی طرفین"},
    )
    assert resp.status_code == 200

    conv = client.post(f"/api/v1/negotiations/{neg_id}/convert-to-contract", headers=headers, json={})
    assert conv.status_code == 201, conv.text
    assert conv.json()["data"]["contract_id"]

    # Analytics reflects won negotiation
    an_res = client.get("/api/v1/negotiations/analytics", headers=headers)
    assert an_res.status_code == 200
    assert an_res.json()["data"]["won_count"] >= 1

    # AI negotiation summary endpoint works
    with patch("django.conf.settings.GAPGPT_API_KEY", ""):
        ai_sum = client.post(
            "/api/v1/ai/negotiation-summary",
            headers=headers,
            json={"negotiation_id": neg_id},
        )
        assert ai_sum.status_code == 200
        assert len(ai_sum.json()["data"]["reply"]) > 15


def test_7_and_8_iranian_payment_gateways_and_localization(settings):
    settings.DEBUG = True  # درگاه mock این سناریو به حالت آزمایشی نیاز دارد.
    client = TestClient(app)

    # Localization endpoint works cleanly with tile_url & phone_prefix
    loc_res = client.get("/api/v1/settings/localization")
    assert loc_res.status_code == 200, loc_res.text
    loc_data = loc_res.json()["data"]
    assert loc_data["map_provider"]["tile_url"].startswith("http")
    assert any(p["key"] == "zarinpal" for p in loc_data["available_adapters"]["payment"])

    super_admin = _login(client, "09120000001", "Admin@12345")
    admin_headers = {"Authorization": f"Bearer {super_admin['access']}"}

    # Save Zarinpal gateway credentials & verify masking
    save_gw = client.post(
        "/api/v1/payments/gateways",
        headers=admin_headers,
        json={
            "provider_key": "zarinpal",
            "display_name": "زرین‌پال تست",
            "is_active": True,
            "is_sandbox": True,
            "priority": 1,
            "credentials": {"merchant_id": "12345678-1234-1234-1234-1234567890ab"},
        },
    )
    assert save_gw.status_code == 200, save_gw.text
    masked = save_gw.json()["data"]["masked_credentials"]["merchant_id"]
    assert "****" in masked
    assert "12345678-1234-1234-1234-1234567890ab" not in masked

    gw_id = save_gw.json()["data"]["id"]
    test_res = client.post(f"/api/v1/payments/gateways/{gw_id}/test", headers=admin_headers)
    assert test_res.status_code == 200
    assert test_res.json()["data"]["ok"] is True

    # Manager initiates payment with Zarinpal + idempotency key + mocked Zarinpal REST v4
    manager = _login(client, "09121111111", "Manager@12345")
    headers = _agency_headers(manager)
    idem_key = f"idem-{uuid.uuid4().hex[:10]}"
    orig_post = httpx.Client.post

    from apps.payments.models import PaymentGatewayTransaction
    from apps.subscriptions.models import AgencySubscription
    from integrations.payment import ZarinpalPaymentAdapter

    agency_id = headers["X-Agency-ID"]
    subscription_count = AgencySubscription.objects.filter(agency_id=agency_id).count()
    transaction_count = PaymentGatewayTransaction.objects.filter(agency_id=agency_id).count()
    with patch.object(ZarinpalPaymentAdapter, "create_payment_intent", side_effect=ValueError("gateway unavailable")):
        rejected = client.post("/api/v1/payments/initiate", headers=headers, json={
            "plan_code": "PRO", "billing_cycle": "MONTHLY", "provider_key": "zarinpal",
            "callback_url": "http://localhost:3000/dashboard/subscriptions", "idempotency_key": idem_key,
        })
    assert rejected.status_code == 502
    assert AgencySubscription.objects.filter(agency_id=agency_id).count() == subscription_count
    assert PaymentGatewayTransaction.objects.filter(agency_id=agency_id).count() == transaction_count

    def fake_zarinpal_post(self, url, *args, **kwargs):
        url_str = str(url)
        if "zarinpal.com" not in url_str:
            return orig_post(self, url, *args, **kwargs)
        req = httpx.Request("POST", url_str)
        if "request.json" in url_str:
            return httpx.Response(200, json={"data": {"code": 100, "authority": f"A000{uuid.uuid4().hex[:8]}"}}, request=req)
        if "verify.json" in url_str:
            return httpx.Response(200, json={"data": {"code": 100, "ref_id": 99887766}}, request=req)
        return httpx.Response(404, json={}, request=req)

    with patch.object(httpx.Client, "post", fake_zarinpal_post):
        init1 = client.post(
            "/api/v1/payments/initiate",
            headers=headers,
            json={
                "plan_code": "PRO",
                "billing_cycle": "MONTHLY",
                "provider_key": "zarinpal",
                "callback_url": "http://localhost:3000/dashboard/subscriptions",
                "idempotency_key": idem_key,
            },
        )
        assert init1.status_code == 201, init1.text
        d1 = init1.json()["data"]
        assert d1["provider_key"] == "zarinpal"
        assert "StartPay" in d1["redirect_url"]

        # Replaying same idempotency_key returns existing transaction without creating duplicate
        init2 = client.post(
            "/api/v1/payments/initiate",
            headers=headers,
            json={
                "plan_code": "PRO",
                "billing_cycle": "MONTHLY",
                "provider_key": "zarinpal",
                "callback_url": "http://localhost:3000/dashboard/subscriptions",
                "idempotency_key": idem_key,
            },
        )
        assert init2.status_code == 201
        assert init2.json()["data"]["transaction_id"] == d1["transaction_id"]
        assert init2.json()["data"]["redirect_url"] == d1["redirect_url"]
        assert init2.json()["data"].get("idempotent_replay") is True

        # Callback verifies and activates subscription once
        cb_res = client.get(f"/api/v1/payments/callback/zarinpal?Authority={d1['authority']}&Status=OK")
        assert cb_res.status_code == 200
        assert cb_res.json()["data"]["status"] == "PAID"
        assert cb_res.json()["data"]["reference_id"] == "99887766"
