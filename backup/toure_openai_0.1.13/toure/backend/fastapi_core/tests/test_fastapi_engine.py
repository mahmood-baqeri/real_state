import os
import sys
from decimal import Decimal
from pathlib import Path
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
from apps.search.services import score_property_for_requirement  # noqa: E402

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


def test_matching_scorer_deterministic():
    prop = {
        "id": "11111111-1111-1111-1111-111111111111",
        "property_code": "PN-1001",
        "title": "Sample Penthouse",
        "deal_type_id": "SALE",
        "property_type_id": "APARTMENT",
        "city": "تهران",
        "district": "زعفرانیه",
        "total_price": Decimal("38000000000"),
        "built_area_sqm": Decimal("185"),
        "bedrooms": 3,
    }
    req = {
        "deal_type_id": "SALE",
        "property_type_id": "APARTMENT",
        "target_city": "تهران",
        "target_districts": ["زعفرانیه"],
        "min_budget": Decimal("20000000000"),
        "max_budget": Decimal("40000000000"),
        "min_area_sqm": Decimal("150"),
        "max_area_sqm": Decimal("220"),
        "min_bedrooms": 3,
    }
    result = score_property_for_requirement(prop, req)
    assert result["match_score"] == 100


def test_fastapi_health():
    client = TestClient(app)
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["data"]["service"] == "fastapi-django-orm"


def test_auth_login_refresh_and_profile():
    client = TestClient(app)
    auth_data = _login(client, "09121111111", "Manager@12345")
    access = auth_data["access"]
    refresh = auth_data["refresh"]
    assert auth_data["user"]["full_name"]

    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me_res.status_code == 200
    assert me_res.json()["data"]["phone_number"] == "09121111111"

    ref_res = client.post("/api/v1/auth/refresh", json={"refresh": refresh})
    assert ref_res.status_code == 200
    assert ref_res.json()["data"]["access"] != ""


def test_tenant_isolation_and_rbac_enforcement():
    client = TestClient(app)
    manager_a = _login(client, "09121111111", "Manager@12345")
    agency_a_id = manager_a["user"]["memberships"][0]["agency_id"]

    # Manager A tries to query Agency B via X-Agency-ID -> fallback/rejected from seeing Agency B items
    from apps.agencies.models import Agency

    agency_b = Agency.objects.filter(slug="arya-home").first()
    assert agency_b is not None
    assert str(agency_b.id) != agency_a_id

    # Manager A sending X-Agency-ID for Agency B falls back to A (cannot see Agency B properties)
    b_props = client.get(
        "/api/v1/properties",
        headers={"Authorization": f"Bearer {manager_a['access']}", "X-Agency-ID": str(agency_b.id)},
    )
    assert b_props.status_code == 200
    for item in b_props.json()["data"]:
        assert item["agency_id"] == agency_a_id

    # Customer cannot access accounting
    customer = _login(client, "09124444444", "Customer@12345")
    acc_res = client.get(
        "/api/v1/accounting/coa",
        headers={"Authorization": f"Bearer {customer['access']}"},
    )
    assert acc_res.status_code == 403

    # Agent cannot access admin users or create commission policies
    agent = _login(client, "09122222222", "Agent@12345")
    admin_res = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {agent['access']}"},
    )
    assert admin_res.status_code == 403

    pol_res = client.post(
        "/api/v1/commissions/policies",
        headers={"Authorization": f"Bearer {agent['access']}", "X-Agency-ID": agency_a_id},
        json={"name": "Unauthorized Policy", "deal_type_id": "SALE"},
    )
    assert pol_res.status_code == 403


def test_subscriptions_and_payroll_endpoints():
    client = TestClient(app)
    manager = _login(client, "09121111111", "Manager@12345")
    headers = {
        "Authorization": f"Bearer {manager['access']}",
        "X-Agency-ID": manager["user"]["memberships"][0]["agency_id"],
    }
    plans_res = client.get("/api/v1/subscriptions/plans")
    assert plans_res.status_code == 200
    assert len(plans_res.json()["data"]) >= 1

    checkout_res = client.post(
        "/api/v1/subscriptions/checkout",
        headers=headers,
        json={"plan_code": "PRO", "billing_cycle": "MONTHLY", "provider_key": "sandbox"},
    )
    assert checkout_res.status_code == 201, checkout_res.text
    authority = checkout_res.json()["data"]["authority"]
    verify_res = client.post(
        "/api/v1/subscriptions/verify",
        headers=headers,
        json={"authority": authority},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["data"]["status"] == "PAID"

    payroll_res = client.get("/api/v1/payroll/cycles", headers=headers)
    assert payroll_res.status_code == 200
    assert len(payroll_res.json()["data"]) >= 1


def test_public_search_address_masking_and_matching():
    client = TestClient(app)
    res = client.get("/api/v1/search/properties?city=تهران")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert len(body["data"]) >= 1
    first = body["data"][0]
    assert "full_address" not in first
    assert "owners" not in first

    prop_id = first["id"]
    det = client.get(f"/api/v1/properties/{prop_id}")
    assert det.status_code == 200
    det_data = det.json()["data"]
    assert "owners" not in det_data
    assert "full_address" not in (det_data.get("location") or {})

    match_res = client.get("/api/v1/matching/customer-to-properties?target_city=تهران")
    assert match_res.status_code == 200
    assert isinstance(match_res.json()["data"], list)

    trends_res = client.get("/api/v1/matching/analytics/price-trends?city=تهران")
    assert trends_res.status_code == 200
    assert isinstance(trends_res.json()["data"], list)


def test_double_entry_accounting_and_lead_conversion():
    client = TestClient(app)
    manager = _login(client, "09121111111", "Manager@12345")
    headers = {
        "Authorization": f"Bearer {manager['access']}",
        "X-Agency-ID": manager["user"]["memberships"][0]["agency_id"],
    }

    coa_res = client.get("/api/v1/accounting/coa", headers=headers)
    assert coa_res.status_code == 200
    coa = coa_res.json()["data"]
    assert len(coa) >= 2

    # Unbalanced journal entry fails with 400
    bad_je = client.post(
        "/api/v1/accounting/journal-entries",
        headers=headers,
        json={
            "entry_number": "JE-BAD-999",
            "description": "Unbalanced test",
            "lines": [
                {"account_id": coa[0]["id"], "description": "Debit", "debit": "500000", "credit": "0"},
                {"account_id": coa[1]["id"], "description": "Credit", "debit": "0", "credit": "300000"},
            ],
        },
    )
    assert bad_je.status_code == 400

    # Balanced journal entry succeeds
    import uuid

    entry_num = f"JE-FA-{uuid.uuid4().hex[:8]}"
    good_je = client.post(
        "/api/v1/accounting/journal-entries",
        headers=headers,
        json={
            "entry_number": entry_num,
            "description": "Balanced test from FastAPI",
            "lines": [
                {"account_id": coa[0]["id"], "description": "Debit", "debit": "500000", "credit": "0"},
                {"account_id": coa[1]["id"], "description": "Credit", "debit": "0", "credit": "500000"},
            ],
        },
    )
    assert good_je.status_code == 201, good_je.text
    je_id = good_je.json()["data"]["id"]

    # Reverse succeeds
    rev_res = client.post(f"/api/v1/accounting/journal-entries/{je_id}/reverse", headers=headers)
    assert rev_res.status_code == 200

    # Create & convert lead
    test_phone = f"0919{uuid.uuid4().int % 10000000:07d}"
    lead_res = client.post(
        "/api/v1/leads",
        headers=headers,
        json={"full_name": "سهراب سپهری", "phone_number": test_phone, "request_type": "BUY"},
    )
    assert lead_res.status_code == 201
    lead_id = lead_res.json()["data"]["id"]
    conv_res = client.post(f"/api/v1/leads/{lead_id}/convert", headers=headers)
    assert conv_res.status_code == 200
    assert conv_res.json()["data"]["customer_id"]


def test_phase5_tickets_complaints_surveys_push_and_ai_isolation():
    client = TestClient(app)
    manager = _login(client, "09121111111", "Manager@12345")
    headers = {
        "Authorization": f"Bearer {manager['access']}",
        "X-Agency-ID": manager["user"]["memberships"][0]["agency_id"],
    }

    # Tickets
    t_res = client.post(
        "/api/v1/tickets",
        headers=headers,
        json={"scope": "AGENCY", "subject": "تیکت تست", "body": "نیازمند بررسی فنی"},
    )
    assert t_res.status_code == 201
    t_id = t_res.json()["data"]["id"]
    rep_res = client.post(
        f"/api/v1/tickets/{t_id}/messages",
        headers=headers,
        json={"body": "پاسخ همکار", "is_internal_note": False},
    )
    assert rep_res.status_code == 201

    # Public complaint submission & tracking
    cmp_res = client.post(
        "/api/v1/complaints/public",
        json={
            "complainant_name": "شهروند",
            "complainant_phone": "09123334455",
            "target_type": "PLATFORM",
            "subject": "گزارش عمومی",
            "description": "بررسی مغایرت آگهی",
            "is_confidential": True,
        },
    )
    assert cmp_res.status_code == 201
    code = cmp_res.json()["data"]["tracking_code"]
    trk_res = client.get(f"/api/v1/complaints/public/track?tracking_code={code}&phone_number=09123334455")
    assert trk_res.status_code == 200
    assert trk_res.json()["data"]["tracking_code"] == code

    # Public seeded survey & analytics
    srv_res = client.get("/api/v1/surveys/public/agency-visit-feedback")
    assert srv_res.status_code == 200
    assert len(srv_res.json()["data"]["questions"]) >= 1

    # Push prefs & VAPID endpoint
    push_key = client.get("/api/v1/push/vapid-public-key")
    assert push_key.status_code == 200
    pref_res = client.get("/api/v1/push/preferences", headers=headers)
    assert pref_res.status_code == 200

    # AI SEO draft & tenant-scoped portfolio insights
    seo_res = client.post(
        "/api/v1/ai/seo-draft",
        headers=headers,
        json={"title": "راهنمای خرید آپارتمان", "target_city": "تهران", "body_excerpt": "نکات حقوقی معامله"},
    )
    assert seo_res.status_code == 200
    assert seo_res.json()["data"]["auto_published"] is False
    ins_res = client.get("/api/v1/ai/portfolio-insights", headers=headers)
    assert ins_res.status_code == 200


def test_phase6_cms_seo_public_requests_and_cooperation():
    client = TestClient(app)

    # Public CMS endpoints
    cats = client.get("/api/v1/cms/public/categories")
    assert cats.status_code == 200
    assert len(cats.json()["data"]) >= 1

    arts = client.get("/api/v1/cms/public/articles")
    assert arts.status_code == 200
    assert len(arts.json()["data"]) >= 1

    faqs = client.get("/api/v1/cms/public/faqs")
    assert faqs.status_code == 200
    assert len(faqs.json()["data"]) >= 1

    jobs = client.get("/api/v1/cms/public/jobs")
    assert jobs.status_code == 200
    assert len(jobs.json()["data"]) >= 1

    # Public contact request + tracking
    inq_res = client.post(
        "/api/v1/public-requests/contact",
        json={
            "full_name": "نگار امینی",
            "phone_number": "09127770011",
            "inquiry_type": "BUY_CONSULT",
            "subject": "خرید ملک در فرشته",
            "message": "لطفاً با من تماس بگیرید.",
        },
    )
    assert inq_res.status_code == 201
    code = inq_res.json()["data"]["tracking_code"]
    trk = client.get(f"/api/v1/public-requests/track?tracking_code={code}&phone_number=09127770011")
    assert trk.status_code == 200
    assert trk.json()["data"]["tracking_code"] == code

    # Agency cooperation submission + super admin approval
    coop_res = client.post(
        "/api/v1/public-requests/cooperation",
        json={
            "agency_name": "هلدینگ املاک تست",
            "city": "شیراز",
            "manager_name": "کامران شیرازی",
            "manager_phone": "09171112233",
            "agents_count": 8,
        },
    )
    assert coop_res.status_code == 201
    coop_id = coop_res.json()["data"]["id"]

    super_admin = _login(client, "09120000001", "Admin@12345")
    rev_res = client.post(
        f"/api/v1/cms/cooperation-requests/{coop_id}/review",
        headers={"Authorization": f"Bearer {super_admin['access']}"},
        json={"decision": "APPROVED"},
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["data"]["approved_agency_id"] is not None


def test_all_nine_roles_login_and_seed_coverage():
    from django.db import connection
    from apps.settings.seeding import collect_domain_model_counts

    assert connection.vendor == "postgresql"
    counts = collect_domain_model_counts()
    empty = [k for k, v in counts.items() if v == 0]
    assert empty == [], f"Expected every domain model seeded, found empty: {empty}"

    client = TestClient(app)
    accounts = [
        ("09120000001", "Admin@12345", "SUPER_ADMIN"),
        ("09121111111", "Manager@12345", "AGENCY_MANAGER"),
        ("09123333333", "Manager@12345", "AGENCY_MANAGER"),
        ("09125555555", "Branch@12345", "BRANCH_MANAGER"),
        ("09127777777", "Sales@12345", "SALES_MANAGER"),
        ("09122222222", "Agent@12345", "AGENT"),
        ("09126666666", "Accountant@12345", "AGENCY_ACCOUNTANT"),
        ("09128888888", "Support@12345", "SUPPORT_AGENT"),
        ("09124444444", "Customer@12345", "CUSTOMER"),
    ]
    for phone, password, expected_role_view in accounts:
        auth_data = _login(client, phone, password)
        headers = {"Authorization": f"Bearer {auth_data['access']}"}
        memberships = auth_data["user"]["memberships"]
        if memberships:
            headers["X-Agency-ID"] = memberships[0]["agency_id"]
        dash_res = client.get("/api/v1/reports/dashboard", headers=headers)
        assert dash_res.status_code == 200, f"Dashboard failed for {phone}: {dash_res.text}"
        assert dash_res.json()["data"]["role_view"] == expected_role_view


def test_global_search_views_calendar_ops_bi_excel_mfa_and_ws():
    import pyotp

    client = TestClient(app)
    manager = _login(client, "09121111111", "Manager@12345")
    headers = {
        "Authorization": f"Bearer {manager['access']}",
        "X-Agency-ID": manager["user"]["memberships"][0]["agency_id"],
    }

    # Global search
    gs = client.get("/api/v1/search/global?q=زعفرانیه", headers=headers)
    assert gs.status_code == 200
    assert gs.json()["data"]["total_hits"] >= 1

    # Saved views CRUD
    sv_create = client.post(
        "/api/v1/search/views",
        headers=headers,
        json={"module": "properties", "title": "تست ویو", "filters_json": {"status": "PUBLISHED"}},
    )
    assert sv_create.status_code == 201
    sv_id = sv_create.json()["data"]["id"]
    assert client.get("/api/v1/search/views?module=properties", headers=headers).status_code == 200
    assert client.delete(f"/api/v1/search/views/{sv_id}", headers=headers).status_code == 200

    # Unified Calendar & Operations Center
    cal = client.get("/api/v1/appointments/calendar?days_ahead=45", headers=headers)
    assert cal.status_code == 200
    assert isinstance(cal.json()["data"], list)

    ops = client.get("/api/v1/reports/operations-center", headers=headers)
    assert ops.status_code == 200
    assert "summary" in ops.json()["data"]

    # BI Analytics
    bi = client.get("/api/v1/reports/analytics?period_days=30", headers=headers)
    assert bi.status_code == 200
    bi_data = bi.json()["data"]
    assert "sales_funnel" in bi_data
    assert "district_breakdown" in bi_data
    assert "activity_heatmap" in bi_data

    # Excel export + Import preview
    exp = client.get("/api/v1/reports/export?module=properties&fmt=xlsx", headers=headers)
    assert exp.status_code == 200
    assert exp.content.startswith(b"PK\x03\x04")

    csv_bytes = "property_code,title,city,district,total_price,built_area_sqm\nIMP-991,واحد تستی,تهران,نیاوران,15000000000,120\n".encode("utf-8")
    imp = client.post(
        "/api/v1/reports/import",
        headers=headers,
        data={"module": "properties", "commit": "false"},
        files={"file": ("test.csv", csv_bytes, "text/csv")},
    )
    assert imp.status_code == 200
    assert imp.json()["data"]["valid_rows"] == 1

    # Property Compare & Timeline
    pub_props = client.get("/api/v1/properties/public").json()["data"]
    assert len(pub_props) >= 2
    cmp_res = client.get(f"/api/v1/properties/compare?ids={pub_props[0]['id']},{pub_props[1]['id']}")
    assert cmp_res.status_code == 200
    assert len(cmp_res.json()["data"]) == 2
    tl_res = client.get(f"/api/v1/properties/{pub_props[0]['id']}/timeline")
    assert tl_res.status_code == 200

    # RSS Topics AI endpoint
    rss_res = client.post("/api/v1/ai/rss-topics", headers=headers, json={})
    assert rss_res.status_code == 200
    assert len(rss_res.json()["data"]["topics"]) >= 1

    # MFA setup -> enable -> login w/ and w/o code -> disable
    agent = _login(client, "09122222222", "Agent@12345")
    ag_headers = {"Authorization": f"Bearer {agent['access']}"}
    mfa_setup = client.post("/api/v1/auth/mfa/setup", headers=ag_headers)
    assert mfa_setup.status_code == 200
    secret = mfa_setup.json()["data"]["secret"]
    totp = pyotp.TOTP(secret)
    assert client.post("/api/v1/auth/mfa/enable", headers=ag_headers, json={"code": totp.now()}).status_code == 200

    no_mfa_login = client.post("/api/v1/auth/login", json={"phone_number": "09122222222", "password": "Agent@12345"})
    assert no_mfa_login.status_code == 401
    with_mfa_login = client.post(
        "/api/v1/auth/login",
        json={"phone_number": "09122222222", "password": "Agent@12345", "mfa_code": totp.now()},
    )
    assert with_mfa_login.status_code == 200
    assert client.post("/api/v1/auth/mfa/disable", headers=ag_headers, json={"code": totp.now()}).status_code == 200

    # WebSocket notification stream
    with client.websocket_connect(f"/api/v1/ws/notifications?token={manager['access']}") as ws:
        msg = ws.receive_json()
        assert msg["event"] == "notification_snapshot"
        assert "unread_count" in msg["data"]


