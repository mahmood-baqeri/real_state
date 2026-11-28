import os
import sys
import uuid
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

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def ensure_seeded_postgres(django_db_setup, django_db_blocker):
    from django.core.cache import cache
    from django.core.management import call_command

    with django_db_blocker.unblock():
        cache.clear()
        call_command("seed_demo", quiet=True)


def _login(client: TestClient, phone: str, password: str) -> dict:
    res = client.post("/api/v1/auth/login", json={"phone_number": phone, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["data"]


def test_sec_01_cross_tenant_isolation():
    """Security Test 1: Tenant A user cannot see Tenant B data."""
    from apps.agencies.models import Agency
    from apps.properties.models import DealType, Property, PropertyType

    client = TestClient(app)
    mgr_a = _login(client, "09121111111", "Manager@12345")
    agency_a_id = mgr_a["user"]["memberships"][0]["agency_id"]
    agency_b = Agency.objects.get(slug="arya-home")

    apt = PropertyType.objects.first()
    sale = DealType.objects.first()
    secret_prop = Property.objects.all_tenants().create(
        agency=agency_b,
        property_code=f"SEC-B-{uuid.uuid4().hex[:6]}",
        title="ملک محرمانه آژانس ب",
        property_type=apt,
        deal_type=sale,
        status=Property.Status.DRAFT,
        visibility=Property.Visibility.PRIVATE_AGENCY,
        total_price=Decimal("1000000000"),
    )
    res = client.get(
        "/api/v1/properties",
        headers={"Authorization": f"Bearer {mgr_a['access']}", "X-Agency-ID": str(agency_b.id)},
    )
    assert res.status_code == 200
    ids = [item["id"] for item in res.json()["data"]]
    assert str(secret_prop.id) not in ids
    assert all(item["agency_id"] == agency_a_id for item in res.json()["data"])


def test_sec_02_idor_url_tampering_blocked():
    """Security Test 2: URL ID tampering (IDOR) returns 403/404."""
    from apps.agencies.models import Agency
    from apps.properties.models import DealType, Property, PropertyType

    client = TestClient(app)
    mgr_a = _login(client, "09121111111", "Manager@12345")
    agency_b = Agency.objects.get(slug="arya-home")

    prop_b = Property.objects.all_tenants().create(
        agency=agency_b,
        property_code=f"IDOR-B-{uuid.uuid4().hex[:6]}",
        title="آگهی خصوصی آژانس دیگر",
        property_type=PropertyType.objects.first(),
        deal_type=DealType.objects.first(),
        status=Property.Status.DRAFT,
        visibility=Property.Visibility.PRIVATE_AGENCY,
        total_price=Decimal("2000000000"),
    )
    res = client.get(
        f"/api/v1/properties/{prop_b.id}",
        headers={
            "Authorization": f"Bearer {mgr_a['access']}",
            "X-Agency-ID": mgr_a["user"]["memberships"][0]["agency_id"],
        },
    )
    assert res.status_code in (403, 404)


def test_sec_03_privilege_escalation_blocked():
    """Security Test 3: Agent/Customer attempting admin/manager role or policy mutation gets 403."""
    client = TestClient(app)
    agent = _login(client, "09122222222", "Agent@12345")
    agency_a_id = agent["user"]["memberships"][0]["agency_id"]
    ag_headers = {"Authorization": f"Bearer {agent['access']}", "X-Agency-ID": agency_a_id}

    assert client.get("/api/v1/admin/users", headers=ag_headers).status_code == 403
    assert (
        client.patch(
            f"/api/v1/agencies/{agency_a_id}/access-policy",
            headers=ag_headers,
            json={"property_view_scope": "ALL_AGENCY"},
        ).status_code
        == 403
    )

    cust = _login(client, "09124444444", "Customer@12345")
    c_headers = {"Authorization": f"Bearer {cust['access']}"}
    assert client.get("/api/v1/admin/subscriptions", headers=c_headers).status_code == 403


def test_sec_04_disabled_user_refresh_rejected():
    """Security Test 4: Deactivated/suspended user cannot refresh token."""
    from apps.accounts.models import User

    client = TestClient(app)
    phone = f"0918{uuid.uuid4().int % 10000000:07d}"
    reg = client.post(
        "/api/v1/auth/register",
        json={"phone_number": phone, "password": "UserPass@123", "first_name": "تست", "last_name": "مسدود"},
    )
    assert reg.status_code == 201
    tokens = _login(client, phone, "UserPass@123")

    User.objects.filter(phone_number=phone).update(status=User.Status.SUSPENDED, is_active=False)
    ref_res = client.post("/api/v1/auth/refresh", json={"refresh": tokens["refresh"]})
    assert ref_res.status_code in (401, 403)


def test_sec_05_revoked_session_fails():
    """Security Test 5: Logged-out / revoked session cannot refresh or access protected endpoints."""
    client = TestClient(app)
    tokens = _login(client, "09124444444", "Customer@12345")
    logout_res = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access']}"},
    )
    assert logout_res.status_code == 200
    ref_res = client.post("/api/v1/auth/refresh", json={"refresh": tokens["refresh"]})
    assert ref_res.status_code == 401
    profile = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access']}"})
    assert profile.status_code == 401


def test_refresh_rotation_requires_current_session_version():
    """دو نسخهٔ خوانده‌شدهٔ نشست فقط یک بار اجازهٔ تغییر شناسه دارند."""
    from apps.accounts.models import UserSession
    from apps.accounts.services import rotate_user_session
    from app.core.security import decode_jwt_token
    from common.exceptions import AuthenticationDomainError

    tokens = _login(TestClient(app), "09124444444", "Customer@12345")
    claims = decode_jwt_token(tokens["refresh"], expected_type="refresh")
    current = UserSession.objects.get(jti=claims["jti"])
    previously_read = UserSession.objects.get(pk=current.pk)
    replacement = uuid.uuid4()
    rotate_user_session(old_session=current, new_jti=replacement)
    with pytest.raises(AuthenticationDomainError):
        rotate_user_session(old_session=previously_read, new_jti=uuid.uuid4())
    current.refresh_from_db()
    assert current.jti == replacement


def test_document_scope_checks_each_linked_record():
    """دامنهٔ قرارداد و ملک سند مستقل از هم در فهرست اسناد بررسی می‌شوند."""
    from django.utils import timezone
    from apps.accounts.models import AgencyMembership
    from apps.contracts.models import Contract
    from apps.documents.models import Document
    from apps.properties.models import Property

    client = TestClient(app)
    tokens = _login(client, "09122222222", "Agent@12345")
    membership = AgencyMembership.objects.get(user_id=tokens["user"]["id"], status="ACTIVE")
    properties = Property.objects.all_tenants().filter(agency_id=membership.agency_id)
    assigned = properties.filter(agent_assignments__membership=membership).first()
    other = properties.exclude(agent_assignments__membership=membership).first()
    assert assigned and other
    contract = Contract.objects.all_tenants().create(
        agency_id=membership.agency_id, property=other, deal_type_id=other.deal_type_id,
        contract_number="DOC-SCOPE", internal_tracking_code="DOC-SCOPE", start_date=timezone.now(),
    )
    allowed = Document.objects.all_tenants().create(
        agency_id=membership.agency_id, property=assigned, title="سند ملک تخصیص‌یافته",
    )
    restricted = Document.objects.all_tenants().create(
        agency_id=membership.agency_id, property=assigned, contract=contract,
        title="سند دارای قرارداد خارج از محدوده",
    )
    result = client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {tokens['access']}", "X-Agency-ID": str(membership.agency_id)},
        params={"property_id": str(assigned.id)},
    )
    assert result.status_code == 200
    ids = {row["id"] for row in result.json()["data"]}
    assert str(allowed.id) in ids
    assert str(restricted.id) not in ids


def test_sec_06_unauthorized_financial_ops_blocked():
    """Security Test 6: Support agent / Customer / Regular agent blocked from accounting & commissions."""
    client = TestClient(app)
    support = _login(client, "09128888888", "Support@12345")
    agency_a_id = support["user"]["memberships"][0]["agency_id"]
    sup_headers = {"Authorization": f"Bearer {support['access']}", "X-Agency-ID": agency_a_id}

    assert client.get("/api/v1/accounting/coa", headers=sup_headers).status_code == 403
    assert client.get("/api/v1/accounting/journal-entries", headers=sup_headers).status_code == 403
    assert (
        client.post(
            "/api/v1/commissions/policies",
            headers=sup_headers,
            json={"name": "Fake", "deal_type_id": "SALE"},
        ).status_code
        == 403
    )


def test_sec_07_malicious_and_spoofed_file_upload_rejected():
    """Security Test 7: Malicious/spoofed file uploads (.exe, .svg XSS, fake .pdf) rejected with 400."""
    client = TestClient(app)
    mgr = _login(client, "09121111111", "Manager@12345")
    headers = {
        "Authorization": f"Bearer {mgr['access']}",
        "X-Agency-ID": mgr["user"]["memberships"][0]["agency_id"],
    }

    # 1. Executable
    exe_res = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={"title": "malware", "category": "GENERAL"},
        files={"file": ("payload.exe", b"MZ\x90\x00evil", "application/octet-stream")},
    )
    assert exe_res.status_code == 400

    # 2. SVG XSS
    svg_res = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={"title": "xss svg", "category": "GENERAL"},
        files={"file": ("xss.svg", b"<svg onload=alert(1)></svg>", "image/svg+xml")},
    )
    assert svg_res.status_code == 400

    # 3. Spoofed PDF without %PDF- magic bytes
    fake_pdf = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={"title": "fake pdf", "category": "GENERAL"},
        files={"file": ("evil.pdf", b"<html><script>alert(1)</script></html>", "application/pdf")},
    )
    assert fake_pdf.status_code == 400

    # 4. Valid PDF succeeds
    valid_pdf = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={"title": "valid deed", "category": "TITLE_DEED"},
        files={"file": ("deed.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n", "application/pdf")},
    )
    assert valid_pdf.status_code == 201


def test_sec_08_bruteforce_lockout_returns_429():
    """Security Test 8: Repeated failed logins trigger Redis brute-force lockout (HTTP 429)."""
    from django.core.cache import cache
    from apps.accounts.models import LoginAttemptLog

    client = TestClient(app)
    phone = f"0915{uuid.uuid4().int % 10000000:07d}"
    cache.delete(f"auth:lockout:{phone}")

    statuses = []
    for _ in range(6):
        res = client.post("/api/v1/auth/login", json={"phone_number": phone, "password": "WrongPassword!1"})
        statuses.append(res.status_code)
    assert 429 in statuses, f"Expected 429 lockout, got {statuses}"
    assert LoginAttemptLog.objects.filter(identifier=phone, succeeded=False).count() == statuses.count(401)
    cache.delete(f"auth:lockout:{phone}")


def test_sec_09_sensitive_ops_recorded_in_audit_log():
    """Security Test 9: Sensitive operations create immutable AuditLog entries."""
    from apps.audit.models import AuditLog

    client = TestClient(app)
    mgr = _login(client, "09121111111", "Manager@12345")
    headers = {
        "Authorization": f"Bearer {mgr['access']}",
        "X-Agency-ID": mgr["user"]["memberships"][0]["agency_id"],
    }
    assert AuditLog.objects.filter(action="USER_LOGIN_SUCCEEDED", actor_id=mgr["user"]["id"]).exists()

    logs_res = client.get("/api/v1/audit/logs?action=USER_LOGIN_SUCCEEDED", headers=headers)
    assert logs_res.status_code == 403
    admin = _login(client, "09120000001", "Admin@12345")
    logs_res = client.get(
        "/api/v1/audit/logs?action=USER_LOGIN_SUCCEEDED",
        headers={"Authorization": f"Bearer {admin['access']}"},
    )
    assert logs_res.status_code == 200
    assert len(logs_res.json()["data"]) >= 1


def test_sec_10_branch_level_permission_isolation():
    """Security Test 10: Branch Manager edits only own branch properties and cannot access cross-branch private edits."""
    from apps.branches.models import Branch
    from apps.properties.models import DealType, Property, PropertyType

    client = TestClient(app)
    branch_mgr = _login(client, "09125555555", "Branch@12345")
    agency_id = branch_mgr["user"]["memberships"][0]["agency_id"]
    other_branch = Branch.objects.all_tenants().filter(agency_id=agency_id, code="TEH-N1").first()
    assert other_branch is not None

    other_prop = Property.objects.all_tenants().create(
        agency_id=agency_id,
        branch=other_branch,
        property_code=f"BR-ISO-{uuid.uuid4().hex[:6]}",
        title="ملک شعبه دیگر",
        property_type=PropertyType.objects.first(),
        deal_type=DealType.objects.first(),
        status=Property.Status.DRAFT,
        total_price=Decimal("12000000000"),
    )
    patch_res = client.patch(
        f"/api/v1/properties/{other_prop.id}",
        headers={"Authorization": f"Bearer {branch_mgr['access']}", "X-Agency-ID": agency_id},
        json={"title": "تلاش ویرایش شعبه دیگر"},
    )
    assert patch_res.status_code == 403
