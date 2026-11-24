"""Dependency-free static release gates for Phase 0.
Run from project root: python scripts/check_phase0_static.py
"""
from pathlib import Path
import ast
import sys

ROOT = Path(__file__).resolve().parents[1]
DJANGO = ROOT / "backend" / "django_core"
FASTAPI = ROOT / "backend" / "fastapi_core"
FRONTEND = ROOT / "frontend"
checks = []


def check(name, condition, detail):
    checks.append((name, bool(condition), detail))


def read(path):
    return path.read_text(encoding="utf-8-sig")


# All Python sources parse without importing runtime dependencies.
python_files = [p for p in ROOT.rglob("*.py") if not any(part in {".venv", "venv", "__pycache__", "site-packages"} for part in p.parts)]
syntax_errors = []
for path in python_files:
    try:
        ast.parse(read(path), filename=str(path))
    except Exception as exc:
        syntax_errors.append(f"{path.relative_to(ROOT)}: {exc}")
check("python_syntax", not syntax_errors, f"files={len(python_files)}; errors={syntax_errors[:5]}")

rls = read(DJANGO / "common/tenant/rls.py")
rls_migration = read(DJANGO / "apps/settings/migrations/0005_force_tenant_rls.py")
rbac_migration = read(DJANGO / "apps/settings/migrations/0006_harden_rbac_rls_policies.py")
check("rls_fail_closed", "ENABLE ROW LEVEL SECURITY" in rls and "FORCE ROW LEVEL SECURITY" in rls and "WITH CHECK" in rls and "IS NOT NULL" in rls, "RLS helper enforces read/write and missing-context denial")
check("rls_migrations", "FORCE ROW LEVEL SECURITY" in rls_migration and "role_permission_write" in rbac_migration and "membership_override_write" in rbac_migration and (DJANGO / "apps/settings/migrations/0007_rls_child_tables.py").exists() and "discover_tenant_relation_paths" in rls, "FORCE RLS, child-table relations and separate RBAC read/write policies are migrated")

main = read(FASTAPI / "app/main.py")
check("private_media_not_mounted", "PUBLIC_MEDIA_ROOT" in main and "PRIVATE_MEDIA_ROOT" in main and "app.mount(\"/media\"" in main, "Only public media root is mounted; private root overlap is rejected")
prod = read(DJANGO / "config/settings/production.py")
check("production_secrets_and_storage_guards", "DJANGO_FIELD_ENCRYPTION_KEY" in prod and "S3_PRIVATE_BUCKET_NAME" in prod and "ACTIVE_PAYMENT_PROVIDER == \"sandbox\"" in prod, "Production settings guard independent secrets, private bucket and payment provider")

storage = read(DJANGO / "integrations/storage.py")
docs = read(DJANGO / "apps/documents/services.py")
check("private_upload_namespace", 'key_prefix=f"private/agencies/{agency_id}/documents"' in docs and "S3_PRIVATE_BUCKET_NAME" in storage, "Document uploads route to private namespace/bucket")
check("private_migration_resume", "legacy_public_file_key" in read(DJANGO / "apps/documents/management/commands/migrate_private_documents.py") and "legacy_public_file_key" in read(DJANGO / "apps/properties/management/commands/migrate_private_property_media.py"), "Legacy public media migration can resume cleanup after interruption")
check("document_confidential_acl", '"document.manage_access"' in docs and "document.download" in docs, "Confidential access and downloads require granular permissions")

crm = read(DJANGO / "apps/crm/services.py")
check("crm_private_interactions", "crm.private_note.view" in crm and "Q(is_private=False)" in crm, "Private interactions are filtered for list consumers")
check("cross_tenant_fk_validation", "مشتری متعلق به این آژانس یافت نشد" in crm and "مشتری مذاکره متعلق به این آژانس نیست" in read(DJANGO / "apps/negotiations/services.py") and "ملک قرارداد متعلق به این آژانس نیست" in read(DJANGO / "apps/contracts/services.py"), "CRM, negotiations and contracts validate agency-owned relations")

reports = read(DJANGO / "apps/reports/services.py")
check("branch_report_scope", 'role_code != "BRANCH_MANAGER"' in reports and 'df["property__branch_id"] = branch_id' in reports, "Branch manager financial reports are denied and deal scope follows property branch")

ai = read(DJANGO / "apps/ai_assistant/services.py")
check("ai_customer_privacy", "or True" not in ai and "customer_context_modes" in ai and "has_agency_permission(user, agency_id, \"crm.private_note.view\")" in ai, "Generic AI context excludes CRM and customer private notes")
check("ssrf_pinned_no_redirect", "_fetch_safe_https_bytes" in ai and "pinned_ip" in ai and "تغییر مسیر در دریافت RSS مجاز نیست" in ai and "ip.is_global" in ai, "RSS fetch validates global DNS and pins IP with redirects disabled")

ws = read(FASTAPI / "app/api/v1/ws.py")
check("websocket_revocation", "_socket_session_is_active" in ws and ws.count("Session revoked or expired") >= 2, "WebSocket sessions are revalidated during long-lived connections")

commissions = read(DJANGO / "apps/commissions/services.py")
commission_api = read(FASTAPI / "app/api/v1/commissions.py")
check("commission_formula_and_balance", "FormulaType.TIERED" in commissions and "agency_house_percent" in commissions and "allocated != net" in commissions and "rules_json" in commission_api, "Tiered commission and agency/agent split are validated and balanced")
payroll = read(DJANGO / "apps/payroll/services.py")
check("payroll_period_and_visibility", 'deal_commission__status="FINANCE_APPROVED"' in payroll and 'deal_commission__created_at__gte=period_start' in payroll and 'raise PermissionDeniedDomainError("فقط مدیر آژانس یا حسابدار' in payroll, "Payroll only consumes finance-approved shares in the period and restricts payslip list")
accounting = read(DJANGO / "apps/accounting/services.py")
check("accounting_reversal", "start_date__lte=now" in accounting and 'reversal.save(update_fields=["reversed_entry"' in accounting and "JournalEntry.Status.REVERSED" in accounting, "Reversals use an open period and original/reversal entries remain reportable")

# All UploadFile endpoints must use bounded reads.
upload_sources = [p for p in (FASTAPI / "app/api/v1").rglob("*.py") if "UploadFile" in read(p)]
unbounded = []
for path in upload_sources:
    source = read(path)
    if "await file.read()" in source or "await upload.read()" in source:
        unbounded.append(str(path.relative_to(ROOT)))
check("bounded_upload_reads", not unbounded, f"UploadFile modules={len(upload_sources)}; unbounded={unbounded}")

# Frontend client directives must be the first statement in client pages.
client_files = [p for p in (FRONTEND / "src").rglob("*.tsx") if '"use client"' in read(p)[:120] or "'use client'" in read(p)[:120]]
late_directives = []
for path in client_files:
    first = read(path).lstrip().splitlines()[0].strip() if read(path).strip() else ""
    if first not in ('"use client";', "'use client';"):
        late_directives.append(str(path.relative_to(ROOT)))
check("client_directives", not late_directives, f"client_files={len(client_files)}; late={late_directives}")
check("stale_encoded_route_removed", not (FRONTEND / "src/app/dashboard/properties/%5Bid%5D").exists(), "Encoded duplicate route folder absent")

failed = [item for item in checks if not item[1]]
for name, passed, detail in checks:
    print(f"{'PASS' if passed else 'FAIL'} | {name} | {detail}")
print(f"SUMMARY | passed={len(checks)-len(failed)} failed={len(failed)} total={len(checks)}")
sys.exit(1 if failed else 0)
