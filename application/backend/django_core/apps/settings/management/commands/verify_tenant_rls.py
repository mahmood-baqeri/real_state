from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from common.tenant.rls import discover_tenant_relation_paths


class Command(BaseCommand):
    help = "Verify PostgreSQL tenant RLS, FORCE RLS, policy coverage and application DB role privileges."

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("Tenant RLS verification requires PostgreSQL; current backend is not PostgreSQL.")

        with connection.cursor() as cursor:
            cursor.execute("SELECT current_user, r.rolsuper, r.rolbypassrls FROM pg_roles r WHERE r.rolname = current_user")
            role_name, is_superuser, bypass_rls = cursor.fetchone()
            if is_superuser or bypass_rls:
                raise CommandError(
                    f"Application DB role {role_name!r} is unsafe: rolsuper={is_superuser}, rolbypassrls={bypass_rls}."
                )

            # Do not report hundreds of missing RLS policies while the migrations
            # that create their tables/policies are still unapplied.
            executor = MigrationExecutor(connection)
            targets = executor.loader.graph.leaf_nodes()
            pending = executor.migration_plan(targets)
            if pending:
                labels = [
                    f"{migration.app_label}.{migration.name}"
                    for migration, backwards in pending
                    if not backwards
                ]
                raise CommandError(
                    "RLS verification blocked by unapplied migrations: "
                    + ", ".join(labels)
                    + ". Back up the database, apply the reviewed migrations, then rerun this check."
                )

            expected = {}
            expected_relations = set()
            for model in apps.get_models(include_auto_created=True):
                if not model._meta.managed:
                    continue
                if model._meta.app_label == "accounts":
                    continue
                try:
                    agency_field = model._meta.get_field("agency")
                except Exception:
                    agency_field = None
                if agency_field is not None:
                    expected[model._meta.db_table] = f"{model._meta.db_table[:40]}_tenant_isolation"
                    if discover_tenant_relation_paths(model, include_self_agency=False):
                        expected_relations.add(model._meta.db_table)
                    continue
                paths = discover_tenant_relation_paths(model, include_self_agency=False)
                if paths:
                    expected[model._meta.db_table] = f"{model._meta.db_table[:40]}_tenant_isolation"
                    expected_relations.add(model._meta.db_table)

            expected.update({
                "audit_log": "audit_log_user_scope",
                "ai_interaction_log": "ai_interaction_log_user_scope",
                "notifications_message": "notifications_message_user_scope",
                "notifications_push_subscription": "notifications_push_subscription_user_scope",
                "notifications_sms_delivery_log": "notifications_sms_delivery_log_user_scope",
                "reports_dashboard_layout": "reports_dashboard_layout_user_scope",
                "reports_onboarding_progress": "reports_onboarding_progress_user_scope",
                "search_saved_view": "search_saved_view_user_scope",
                "search_saved_search": "search_saved_search_user_scope",
                "notifications_preference": "notifications_preference_user_scope",
                "accounts_user_session": "accounts_user_session_user_scope",
                "accounts_websocket_ticket": "accounts_websocket_ticket_user_scope",
                "support_ticket": "support_ticket_user_scope",
                "complaints_complaint": "complaints_complaint_user_scope",
                "notifications_sms_template": "notifications_sms_template_platform_only",
                "accounts_login_attempt_log": "accounts_login_attempt_log_platform_only",
                "accounts_agency_membership": "membership_tenant_write",
                "accounts_role": "role_tenant_write",
                "accounts_role_permission": "role_permission_write",
                "accounts_membership_permission_override": "membership_override_write",
            })
            cursor.execute("""
                SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity,
                       p.policyname, p.qual, p.with_check
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                LEFT JOIN pg_policies p ON p.schemaname = n.nspname AND p.tablename = c.relname
                WHERE n.nspname = current_schema() AND c.relkind = 'r'
            """)
            actual = {}
            for table, enabled, forced, policy, qual, with_check in cursor.fetchall():
                entry = actual.setdefault(table, {"enabled": enabled, "forced": forced, "policies": {}})
                if policy:
                    entry["policies"][policy] = (qual or "", with_check or "")

        missing = []
        custom_tables = {
            "audit_log", "ai_interaction_log", "notifications_message", "notifications_push_subscription",
            "notifications_sms_delivery_log", "reports_dashboard_layout", "reports_onboarding_progress",
            "search_saved_view", "search_saved_search", "notifications_preference",
            "accounts_user_session", "accounts_websocket_ticket", "support_ticket",
            "complaints_complaint", "notifications_sms_template", "accounts_login_attempt_log",
        }
        for table, policy in expected.items():
            if table not in actual:
                # An unapplied app migration is already a project migration failure;
                # report it explicitly rather than silently skipping the table.
                missing.append(f"{table}: table missing")
                continue
            entry = actual[table]
            if not entry["enabled"]:
                missing.append(f"{table}: RLS disabled")
            if not entry["forced"]:
                missing.append(f"{table}: FORCE RLS disabled")
            if policy not in entry["policies"]:
                missing.append(f"{table}: policy {policy} missing")
            elif not entry["policies"][policy][1]:
                missing.append(f"{table}: WITH CHECK predicate missing")
            elif table in expected_relations and table not in custom_tables:
                qual, with_check = entry["policies"][policy]
                if "EXISTS" not in qual.upper() or "EXISTS" not in with_check.upper():
                    missing.append(f"{table}: tenant FK relationship predicate missing")
            if table in custom_tables and policy in entry["policies"]:
                qual, with_check = entry["policies"][policy]
                if table in {"notifications_sms_template", "accounts_login_attempt_log"}:
                    if "app.tenant_bypass" not in qual or "app.tenant_bypass" not in with_check:
                        missing.append(f"{table}: platform-only bypass predicate missing")
                elif "app.current_user_id" not in qual or "app.current_user_id" not in with_check:
                    missing.append(f"{table}: user ownership predicate missing")

        if missing:
            raise CommandError("Tenant RLS verification failed:\n- " + "\n- ".join(missing))
        self.stdout.write(self.style.SUCCESS(
            f"Tenant RLS verified: {len(expected)} tables, ENABLE + FORCE + policy coverage; DB role={role_name} is not SUPERUSER/BYPASSRLS."
        ))
