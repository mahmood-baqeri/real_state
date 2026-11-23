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


def test_1_global_settings_registry_secrets_override_cache_and_rollback():
    client = TestClient(app)
    super_admin = _login(client, "09120000001", "Admin@12345")
    admin_headers = {"Authorization": f"Bearer {super_admin['access']}"}

    # Bootstrap exposes public settings and masks secrets
    boot1 = client.get("/api/v1/settings/public-bootstrap")
    assert boot1.status_code == 200
    assert boot1.json()["data"]["public_settings"].get("general.platform_name_fa")

    # Update public setting & secret setting (create_if_missing), verify masking and live cache invalidation
    new_name = f"بنیان ملک تست {uuid.uuid4().hex[:4]}"
    upd = client.put(
        "/api/v1/settings/registry",
        headers=admin_headers,
        json={
            "updates": [
                {"key": "general.platform_name_fa", "value": new_name},
                {
                    "key": "security.webhook_hmac_secret",
                    "value": "secret-hmac-token-9988",
                    "create_if_missing": True,
                    "title_fa": "کلید امضای وب‌هوک",
                    "category": "SECURITY",
                    "value_type": "SECRET",
                    "sensitivity_level": "SECRET",
                },
            ],
            "change_reason": "تست ذخیره و رمزنگاری تنظیمات",
        },
    )
    assert upd.status_code == 200, upd.text
    items = {x["key"]: x for x in upd.json()["data"]}
    assert items["general.platform_name_fa"]["value"] == new_name
    assert items["security.webhook_hmac_secret"]["value"] == "****"
    assert items["security.webhook_hmac_secret"]["has_secret_value"] is True

    boot2 = client.get("/api/v1/settings/public-bootstrap")
    assert boot2.json()["data"]["public_settings"]["general.platform_name_fa"] == new_name

    # History & Rollback
    hist = client.get("/api/v1/settings/registry/history?setting_key=general.platform_name_fa", headers=admin_headers)
    assert hist.status_code == 200
    assert len(hist.json()["data"]) >= 1
    hist_id = hist.json()["data"][0]["id"]

    rb = client.post(f"/api/v1/settings/registry/rollback/{hist_id}", headers=admin_headers)
    assert rb.status_code == 200
    assert rb.json()["data"]["value"] != new_name

    # Agency override takes precedence over platform default for agency context
    manager = _login(client, "09121111111", "Manager@12345")
    mgr_headers = _agency_headers(manager)
    ov = client.put(
        "/api/v1/settings/registry",
        headers=mgr_headers,
        json={
            "updates": [{"key": "property.default_featured_limit_agency", "value": 35}],
            "change_reason": "تنظیم اختصاصی آژانس",
        },
    )
    assert ov.status_code == 200, ov.text
    mgr_reg = client.get("/api/v1/settings/registry?category=PROPERTY", headers=mgr_headers)
    assert mgr_reg.status_code == 200, mgr_reg.text
    vis = next(x for x in mgr_reg.json()["data"] if x["key"] == "property.default_featured_limit_agency")
    assert vis["value"] == 35


def test_2_dynamic_countries_calendars_currencies_and_fx_snapshot():
    client = TestClient(app)
    super_admin = _login(client, "09120000001", "Admin@12345")
    admin_headers = {"Authorization": f"Bearer {super_admin['access']}"}

    # Create/Update currency (GBP) and Country (GB) and Calendar (hijri_demo)
    cur_res = client.post(
        "/api/v1/settings/currencies",
        headers=admin_headers,
        json={
            "code": "GBP",
            "name_fa": "پوند بریتانیا",
            "name_en": "British Pound",
            "symbol": "£",
            "decimal_places": 2,
            "minor_unit": "Pence",
            "base_unit_factor": "82000.000000",
            "sort_order": 50,
            "is_active": True,
        },
    )
    assert cur_res.status_code == 201, cur_res.text

    fx_res = client.post(
        "/api/v1/settings/exchange-rates",
        headers=admin_headers,
        json={
            "base_currency_code": "GBP",
            "quote_currency_code": "IRT",
            "rate": "82500.50000000",
            "source": "TEST_ORACLE",
            "is_active": True,
            "change_reason": "ثبت نرخ مرجع تست",
        },
    )
    assert fx_res.status_code == 201, fx_res.text
    assert Decimal(fx_res.json()["data"]["rate"]) == Decimal("82500.50000000")

    country_res = client.post(
        "/api/v1/settings/countries",
        headers=admin_headers,
        json={
            "code": "GB",
            "alpha3_code": "GBR",
            "name_fa": "بریتانیا",
            "name_en": "United Kingdom",
            "default_currency_code": "GBP",
            "default_calendar": "gregorian",
            "supported_calendars": ["gregorian"],
            "default_language": "en",
            "supported_languages": ["en", "fa"],
            "default_timezone": "Europe/London",
            "phone_prefix": "+44",
            "is_active": True,
        },
    )
    assert country_res.status_code == 201, country_res.text

    # Toggle currency off and back on via PATCH
    t1 = client.patch("/api/v1/settings/currencies/GBP/toggle", headers=admin_headers, json={"is_active": False})
    assert t1.status_code == 200 and t1.json()["data"]["is_active"] is False
    t2 = client.patch("/api/v1/settings/currencies/GBP/toggle", headers=admin_headers, json={"is_active": True})
    assert t2.status_code == 200 and t2.json()["data"]["is_active"] is True

    # Verify FX snapshot saved on Deal and PaymentGatewayTransaction
    manager = _login(client, "09121111111", "Manager@12345")
    mgr_headers = _agency_headers(manager)
    props = client.get("/api/v1/properties", headers=mgr_headers).json()["data"]
    assert len(props) >= 1

    contract_res = client.post(
        "/api/v1/contracts",
        headers=mgr_headers,
        json={
            "contract_number": f"FXC-{uuid.uuid4().hex[:6]}",
            "contract_type": "SALE",
            "property_id": props[0]["id"],
            "deal_type_id": "SALE",
            "currency_id": "GBP",
            "amount": "100000",
            "status": "ACTIVE",
        },
    )
    assert contract_res.status_code == 201, contract_res.text

    deal_res = client.post(
        "/api/v1/deals",
        headers=mgr_headers,
        json={
            "deal_code": f"FXD-{uuid.uuid4().hex[:6]}",
            "contract_id": contract_res.json()["data"]["id"],
            "currency_id": "GBP",
            "deal_value": "100000",
        },
    )
    assert deal_res.status_code == 201, deal_res.text

    from apps.transactions.models import Deal

    deal_obj = Deal.objects.get(id=deal_res.json()["data"]["id"])
    assert deal_obj.exchange_rate_snapshot == Decimal("82500.50000000")

    # Payment transaction FX snapshot verification
    orig_post = httpx.Client.post

    def fake_zp(self, url, *args, **kwargs):
        if "zarinpal.com" not in str(url):
            return orig_post(self, url, *args, **kwargs)
        req = httpx.Request("POST", str(url))
        return httpx.Response(200, json={"data": {"code": 100, "authority": f"AFX{uuid.uuid4().hex[:8]}"}}, request=req)

    with patch.object(httpx.Client, "post", fake_zp):
        pay_res = client.post(
            "/api/v1/payments/initiate",
            headers=mgr_headers,
            json={
                "plan_code": "PRO",
                "billing_cycle": "MONTHLY",
                "provider_key": "sandbox",
                "callback_url": "http://localhost:3000/dashboard/subscriptions",
                "idempotency_key": f"fxpay-{uuid.uuid4().hex[:8]}",
            },
        )
        assert pay_res.status_code == 201, pay_res.text
        from apps.payments.models import PaymentGatewayTransaction

        tx = PaymentGatewayTransaction.objects.get(id=pay_res.json()["data"]["transaction_id"])
        assert tx.exchange_rate_snapshot is not None
        assert tx.exchange_rate_snapshot > Decimal("0")


def test_3_sms_templates_event_blocking_and_masked_logs():
    client = TestClient(app)
    super_admin = _login(client, "09120000001", "Admin@12345")
    admin_headers = {"Authorization": f"Bearer {super_admin['access']}"}

    tpl_key = f"test_tpl_{uuid.uuid4().hex[:5]}"
    tpl_res = client.post(
        "/api/v1/notifications/sms/templates",
        headers=admin_headers,
        json={
            "key": tpl_key,
            "event_type": "GENERAL",
            "name_fa": "قالب تست",
            "body_template": "کد تایید شما: {code}",
            "sample_tokens": ["code"],
            "is_active": True,
        },
    )
    assert tpl_res.status_code == 201, tpl_res.text

    # Test SMS sends with masked phone
    send_ok = client.post(
        "/api/v1/notifications/sms/test",
        headers=admin_headers,
        json={"phone_number": "09129998877", "template_key": tpl_key},
    )
    assert send_ok.status_code == 200, send_ok.text

    # Disable global sms.enabled -> subsequent dispatch logs BLOCKED_BY_TOGGLE
    client.put(
        "/api/v1/settings/registry",
        headers=admin_headers,
        json={"updates": [{"key": "sms.enabled", "value": False}], "change_reason": "تست توقف پیامک"},
    )
    send_blk = client.post(
        "/api/v1/notifications/sms/test",
        headers=admin_headers,
        json={"phone_number": "09129998877", "message": "پیامک مسدودشده"},
    )
    assert send_blk.status_code == 200
    assert send_blk.json()["data"]["status"] == "BLOCKED_BY_TOGGLE"

    # Re-enable sms.enabled
    client.put(
        "/api/v1/settings/registry",
        headers=admin_headers,
        json={"updates": [{"key": "sms.enabled", "value": True}], "change_reason": "فعال‌سازی مجدد"},
    )

    logs = client.get("/api/v1/notifications/sms/logs", headers=admin_headers)
    assert logs.status_code == 200
    assert any("***" in item["recipient_masked"] for item in logs.json()["data"])
    assert all("09129998877" not in item["recipient_masked"] for item in logs.json()["data"])


def test_4_security_session_console_and_emergency_force_logout():
    client = TestClient(app)
    super_admin = _login(client, "09120000001", "Admin@12345")
    admin_headers = {"Authorization": f"Bearer {super_admin['access']}"}

    # Second user login creates another active session
    agent = _login(client, "09122222222", "Agent@12345")
    agent_headers = {"Authorization": f"Bearer {agent['access']}"}

    sessions_res = client.get("/api/v1/auth/admin/sessions", headers=admin_headers)
    assert sessions_res.status_code == 200
    assert len(sessions_res.json()["data"]) >= 2

    # Wrong password_confirm fails on emergency force logout
    bad_panic = client.post(
        "/api/v1/auth/admin/emergency-force-logout",
        headers=admin_headers,
        json={"password_confirm": "WrongPass!999", "exclude_current": True},
    )
    assert bad_panic.status_code in (400, 401, 403), bad_panic.text

    # Correct password_confirm revokes all other sessions while preserving current if exclude_current=True
    ok_panic = client.post(
        "/api/v1/auth/admin/emergency-force-logout",
        headers=admin_headers,
        json={"password_confirm": "Admin@12345", "exclude_current": True},
    )
    assert ok_panic.status_code == 200, ok_panic.text
    assert ok_panic.json()["data"]["revoked_count"] >= 1

    # Revoked agent token should now be rejected
    rejected = client.get("/api/v1/auth/me", headers=agent_headers)
    assert rejected.status_code == 401


def test_5_legal_cms_xss_sanitization_lifecycle_version_restore_and_acceptance():
    client = TestClient(app)
    super_admin = _login(client, "09120000001", "Admin@12345")
    admin_headers = {"Authorization": f"Bearer {super_admin['access']}"}

    slug = f"legal-test-{uuid.uuid4().hex[:5]}"
    v1_res = client.post(
        "/api/v1/cms/legal",
        headers=admin_headers,
        json={
            "slug": slug,
            "doc_type": "LEGAL",
            "title_fa": "سند تست نسخه ۱",
            "summary": "خلاصه اول",
            "body_html": "<h2>بند ۱</h2><p>متن امن</p><script>alert('xss')</script>",
            "status": "DRAFT",
            "requires_acceptance": True,
            "change_note": "نسخه اولیه",
        },
    )
    assert v1_res.status_code == 201, v1_res.text
    doc = v1_res.json()["data"]
    assert "<script" not in doc["body_html"].lower()

    # Update to version 2 and publish
    v2_res = client.post(
        "/api/v1/cms/legal",
        headers=admin_headers,
        json={
            "slug": slug,
            "doc_type": "LEGAL",
            "title_fa": "سند تست نسخه ۲",
            "summary": "خلاصه دوم",
            "body_html": "<h2>بند ۲</h2><p>متن ویرایش‌شده</p>",
            "status": "PUBLISHED",
            "requires_acceptance": True,
            "change_note": "انتشار نسخه ۲",
        },
    )
    assert v2_res.status_code == 201
    assert v2_res.json()["data"]["version_number"] == 2

    # User accepts published document
    acc_res = client.post(f"/api/v1/legal/{slug}/accept", headers=admin_headers)
    assert acc_res.status_code == 200
    assert acc_res.json()["data"]["version_number"] == 2

    # Restore version 1 creates version 3 with version 1's title
    rest_res = client.post(f"/api/v1/cms/legal/{doc['id']}/restore/1", headers=admin_headers)
    assert rest_res.status_code == 200
    assert rest_res.json()["data"]["title_fa"] == "سند تست نسخه ۱"

    # Transition PUBLISHED -> ARCHIVED works
    arch_res = client.post(
        f"/api/v1/cms/legal/{doc['id']}/status",
        headers=admin_headers,
        json={"status": "ARCHIVED"},
    )
    assert arch_res.status_code == 200
    assert arch_res.json()["data"]["status"] == "ARCHIVED"


def test_6_property_verification_anomalies_exception_override_and_violations():
    client = TestClient(app)
    manager = _login(client, "09121111111", "Manager@12345")
    mgr_headers = _agency_headers(manager)
    super_admin = _login(client, "09120000001", "Admin@12345")
    admin_headers = {"Authorization": f"Bearer {super_admin['access']}"}

    tehran_city = next(
        c for c in client.get("/api/v1/locations/cities").json()["data"] if c["name_fa"] == "تهران"
    )
    code = f"VER-{uuid.uuid4().hex[:6].upper()}"
    # Deliberately low price_per_sqm triggers anomaly flag
    prop_res = client.post(
        "/api/v1/properties",
        headers=mgr_headers,
        json={
            "property_code": code,
            "title": "ملک تست احراز اصالت و تخلف",
            "property_type_id": "APARTMENT",
            "deal_type_id": "SALE",
            "built_area_sqm": "100",
            "total_price": "100000",  # abnormally low price for 100 sqm
            "location": {"city_id": tehran_city["id"]},
        },
    )
    assert prop_res.status_code == 201, prop_res.text
    prop_id = prop_res.json()["data"]["id"]

    # Check verification & anomaly flags
    ver_get = client.get(f"/api/v1/properties/{prop_id}/verification", headers=mgr_headers)
    assert ver_get.status_code == 200
    assert len(ver_get.json()["data"]["anomaly_flags"]) >= 1

    # Unverified publish blocked
    blk = client.post(f"/api/v1/properties/{prop_id}/publish", headers=mgr_headers)
    assert blk.status_code in (400, 422)

    # Exception override with mandatory reason enables publishing + records AuditLog
    ov_res = client.put(
        f"/api/v1/properties/{prop_id}/verification",
        headers=mgr_headers,
        json={"exception_override": True, "override_reason": "تأیید اضطراری مدیر شعبه برای تست سامانه"},
    )
    assert ov_res.status_code == 200
    assert ov_res.json()["data"]["verification_status"] == "EXCEPTION_APPROVED"

    pub_ok = client.post(f"/api/v1/properties/{prop_id}/publish", headers=mgr_headers)
    assert pub_ok.status_code == 200

    # Public violation report + Admin suspend resolution
    vio_res = client.post(
        f"/api/v1/properties/{prop_id}/violations",
        json={"reason_type": "FAKE_PRICE", "details": "قیمت ثبت‌شده با واقعیت بازار مغایرت دارد."},
    )
    assert vio_res.status_code == 201
    report_id = vio_res.json()["data"]["id"]

    res_adm = client.post(
        f"/api/v1/properties/violations/{report_id}/resolve",
        headers=admin_headers,
        json={
            "resolution_status": "RESOLVED_SUSPENDED",
            "resolution_note": "تایید تخلف قیمت صوری و تعلیق آگهی",
            "suspend_listing": True,
        },
    )
    assert res_adm.status_code == 200, res_adm.text

    prop_after = client.get(f"/api/v1/properties/{prop_id}", headers=mgr_headers).json()["data"]
    assert prop_after["status"] != "PUBLISHED"


def test_7_customer_export_pii_masking_and_subscription_quotas():
    client = TestClient(app)
    agent = _login(client, "09122222222", "Agent@12345")
    agent_headers = _agency_headers(agent)

    # Agent CSV export masks customer phones and logs DATA_EXPORTED audit event
    exp_res = client.get("/api/v1/reports/export?module=customers&fmt=csv", headers=agent_headers)
    assert exp_res.status_code == 200
    csv_text = exp_res.content.decode("utf-8-sig")
    assert "***" in csv_text or "****" in csv_text

    from apps.audit.models import AuditLog

    assert AuditLog.objects.filter(action="DATA_EXPORTED").exists()

    # Enforce active subscription max_branches quota
    manager = _login(client, "09121111111", "Manager@12345")
    mgr_headers = _agency_headers(manager)
    agency_id = manager["user"]["memberships"][0]["agency_id"]

    from apps.branches.models import Branch
    from apps.subscriptions.models import AgencySubscription

    sub = AgencySubscription.objects.filter(agency_id=agency_id).order_by("-created_at").first()
    if sub:
        sub.plan.max_branches = Branch.objects.all_tenants().filter(agency_id=agency_id, is_active=True).count()
        sub.plan.save(update_fields=["max_branches"])

        quota_err = client.post(
            f"/api/v1/agencies/{agency_id}/branches",
            headers=mgr_headers,
            json={"name": "شعبه مازاد بر سهمیه", "code": f"BR-{uuid.uuid4().hex[:4]}"},
        )
        assert quota_err.status_code in (400, 403), quota_err.text


def test_site_content_blocks_use_slug_key_as_primary_key_in_api():
    """Regression: SiteContentBlock uses slug_key (not an implicit id) as its PK."""
    client = TestClient(app)
    super_admin = _login(client, "09120000001", "Admin@12345")
    admin_headers = {"Authorization": f"Bearer {super_admin['access']}"}
    slug = f"regression-content-{uuid.uuid4().hex[:10]}"

    saved = client.put(
        f"/api/v1/settings/content-blocks/{slug}",
        headers=admin_headers,
        json={
            "page_key": "HOME",
            "section_key": "REGRESSION",
            "title_fa": "آزمون شناسه بلوک محتوا",
            "body_html": "<p>Regression test</p>",
            "status": "PUBLISHED",
            "is_active": True,
        },
    )
    assert saved.status_code == 200, saved.text
    saved_data = saved.json()["data"]
    assert saved_data["id"] == slug
    assert saved_data["slug_key"] == slug

    listed = client.get("/api/v1/settings/content-blocks?published_only=false")
    assert listed.status_code == 200, listed.text
    listed_data = next(item for item in listed.json()["data"] if item["slug_key"] == slug)
    assert listed_data["id"] == slug

def test_branding_endpoints_use_slot_key_as_primary_key():
    """BrandMediaSlot has a string PK named slot_key, not an implicit id."""
    client = TestClient(app)

    listing = client.get("/api/v1/settings/branding?include_inactive=true")
    assert listing.status_code == 200, listing.text
    slots = listing.json()["data"]
    assert slots
    assert all(item["id"] == item["slot_key"] for item in slots)

    super_admin = _login(client, "09120000001", "Admin@12345")
    headers = {"Authorization": f"Bearer {super_admin['access']}"}
    slot_key = slots[0]["slot_key"]
    updated = client.put(
        f"/api/v1/settings/branding/{slot_key}",
        headers=headers,
        json={"title_fa": slots[0]["title_fa"]},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["id"] == slot_key
    assert updated.json()["data"]["slot_key"] == slot_key



def test_platform_visual_presets_and_custom_palette_can_be_saved_and_bootstrapped():
    client = TestClient(app)
    super_admin = _login(client, "09120000001", "Admin@12345")
    headers = {"Authorization": f"Bearer {super_admin['access']}"}
    presets = ["glass", "neo", "organic", "custom"]

    for preset in presets:
        response = client.put(
            "/api/v1/settings/registry",
            headers=headers,
            json={
                "updates": [{"key": "branding.default_theme_preset", "value": preset}],
                "change_reason": "تست سبک‌های بصری و پالت اختصاصی",
            },
        )
        assert response.status_code == 200, f"preset={preset}: {response.text}"
        bootstrap = client.get("/api/v1/settings/public-bootstrap")
        assert bootstrap.status_code == 200, bootstrap.text
        assert bootstrap.json()["data"]["public_settings"]["branding.default_theme_preset"] == preset
