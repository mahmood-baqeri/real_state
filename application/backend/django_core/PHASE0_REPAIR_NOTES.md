# Phase 0 repair package

## Changes included

1. `tests/test_phase0_additional_controls.py`
   - Changed `TenantBypassNestingTests` from Django `TestCase` to `SimpleTestCase`.
   - The test only exercises context-manager/context-local state and does not query the database. It therefore must not force pytest-django to create `test_real_state`, which requires CREATEDB privileges from the application role.

2. `apps/settings/migrations/0007_rls_child_tables.py`
   - Added `ALTER TABLE ... FORCE ROW LEVEL SECURITY` after creating RLS policies for direct-agency tables.
   - Migration 0005 forced only models with non-null `agency`; nullable-agency direct tables were left without FORCE, while the verifier requires FORCE.

3. `apps/settings/management/commands/verify_tenant_rls.py`
   - Added a migration preflight. If migrations are pending, verification now stops with the exact migration names instead of reporting hundreds of derivative “RLS disabled / policy missing” messages.
   - It still rejects SUPERUSER and BYPASSRLS application roles.

4. `apps/accounting/models.py`
   - Replaced deprecated `CheckConstraint(check=...)` with `CheckConstraint(condition=...)`.

## What the supplied report proves

The latest report (`20261124_103705`) lists these unapplied migrations:

- `accounts.0004_websocketticket`
- `documents.0003_documentversion_legacy_public_file_key`
- `payroll.0002_payroll_cancellation_states`
- `payroll.0003_payrollcycle_cancelled_status`
- `property_media.0002_propertymedia_legacy_public_file_key`
- `settings.0004_enable_tenant_rls`
- `settings.0005_force_tenant_rls`
- `settings.0006_harden_rbac_rls_policies`
- `settings.0007_rls_child_tables`

The missing `accounts_websocket_ticket` table is explained by the unapplied `accounts.0004_websocketticket` migration. The RLS errors are also expected before the RLS migrations have been applied; they are not evidence that every individual table migration is missing.

## Required deployment sequence

Do not delete the database and do not grant CREATEDB, SUPERUSER, or BYPASSRLS to the runtime application role.

1. Take and verify a database backup.
2. Confirm the configured migration role owns the affected schema/tables (or has the required DDL privileges) and is neither SUPERUSER nor BYPASSRLS.
3. Review the pending migration plan against the current database, then apply the pending migrations with the project's normal Django migration command.
4. Run `python manage.py verify_tenant_rls` using the normal, non-superuser application role.
5. Rerun the Phase 0 validation script.

## Validation runner

The current `backend.zip` did not include the project-root `check_phase0.ps1`. I restored the copy previously supplied in `phase0_patch_v3.zip` and changed its database-check order so that the migration plan is reported before RLS verification. If the local script has changed since that earlier copy, compare it before replacing it.

## Validation limits

No live PostgreSQL instance or project virtual environment was available here. The modified Python files passed Python syntax compilation, and the output archive passed ZIP integrity validation; Django tests, migrations, and actual PostgreSQL RLS enforcement were not executable in this environment.
