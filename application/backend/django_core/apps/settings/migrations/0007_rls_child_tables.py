from django.db import migrations


def apply_child_table_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    from common.tenant.rls import (
        discover_tenant_relation_paths,
        generate_related_rls_policy_sql,
        generate_rls_policy_sql,
        generate_user_scope_policy_sql,
    )
    tables = set(schema_editor.connection.introspection.table_names())
    for model in apps.get_models(include_auto_created=True):
        if model._meta.app_label == "accounts" or not model._meta.managed:
            continue
        table = model._meta.db_table
        if table not in tables:
            continue
        try:
            agency_field = model._meta.get_field("agency")
        except Exception:
            agency_field = None
        paths = discover_tenant_relation_paths(model, include_self_agency=False)
        if agency_field is not None:
            schema_editor.execute(generate_rls_policy_sql(
                table, agency_field.column, paths, allow_global_rows=False,
                allow_related_rows=agency_field.null
            ))
        elif paths:
            schema_editor.execute(generate_related_rls_policy_sql(table, paths))

    user_scope_specs = {
        "audit_log": (["actor_id"], "agency_id", True),
        "ai_interaction_log": (["user_id"], "agency_id", False),
        "notifications_message": (["recipient_id"], "agency_id", False),
        "notifications_push_subscription": (["user_id"], "agency_id", False),
        "notifications_sms_delivery_log": (["actor_id"], "agency_id", False),
        "reports_dashboard_layout": (["user_id"], "agency_id", False),
        "reports_onboarding_progress": (["user_id"], "agency_id", False),
        "search_saved_view": (["user_id"], "agency_id", False),
        "search_saved_search": (["user_id"], None, False),
        "notifications_preference": (["user_id"], None, False),
        "accounts_user_session": (["user_id"], None, False),
        "accounts_websocket_ticket": (["user_id"], "agency_id", False),
        "support_ticket": (["created_by_user_id", "assigned_to_user_id"], "agency_id", True),
        "complaints_complaint": (["complainant_user_id", "assigned_to_user_id"], "agency_id", True),
    }
    for table, (user_columns, agency_column, agency_scope) in user_scope_specs.items():
        if table not in tables:
            continue
        schema_editor.execute(f'DROP POLICY IF EXISTS "{table[:40]}_tenant_isolation" ON "{table}"')
        schema_editor.execute(generate_user_scope_policy_sql(
            table, user_columns, agency_column=agency_column, agency_scope=agency_scope
        ))

    for table in ("notifications_sms_template", "accounts_login_attempt_log"):
        if table in tables:
            schema_editor.execute(f'DROP POLICY IF EXISTS "{table[:40]}_tenant_isolation" ON "{table}"')
            schema_editor.execute(generate_user_scope_policy_sql(table, bypass_only=True))


def reverse_child_table_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    from common.tenant.rls import (
        discover_tenant_relation_paths,
        generate_related_rls_policy_sql,
        generate_rls_policy_sql,
    )
    tables = set(schema_editor.connection.introspection.table_names())
    user_scope_specs = {
        "audit_log": "user_scope",
        "ai_interaction_log": "user_scope",
        "notifications_message": "user_scope",
        "notifications_push_subscription": "user_scope",
        "notifications_sms_delivery_log": "user_scope",
        "reports_dashboard_layout": "user_scope",
        "reports_onboarding_progress": "user_scope",
        "search_saved_view": "user_scope",
        "search_saved_search": "user_scope",
        "notifications_preference": "user_scope",
        "accounts_user_session": "user_scope",
        "accounts_websocket_ticket": "user_scope",
        "support_ticket": "user_scope",
        "complaints_complaint": "user_scope",
        "notifications_sms_template": "platform_only",
        "accounts_login_attempt_log": "platform_only",
    }
    for table, suffix in user_scope_specs.items():
        if table in tables:
            schema_editor.execute(f'DROP POLICY IF EXISTS "{table[:40]}_{suffix}" ON "{table}"')

    for model in apps.get_models(include_auto_created=True):
        if model._meta.app_label == "accounts" or not model._meta.managed:
            continue
        table = model._meta.db_table
        if table not in tables:
            continue
        try:
            agency_field = model._meta.get_field("agency")
        except Exception:
            agency_field = None
        paths = discover_tenant_relation_paths(model, include_self_agency=False)
        if agency_field is not None:
            schema_editor.execute(generate_rls_policy_sql(
                table, agency_field.column, paths, allow_global_rows=False,
                allow_related_rows=agency_field.null
            ))
        elif paths and not model._meta.auto_created:
            schema_editor.execute(generate_related_rls_policy_sql(table, paths))
        elif paths and model._meta.auto_created:
            policy = f"{table[:40]}_tenant_isolation"
            schema_editor.execute(f'DROP POLICY IF EXISTS "{policy}" ON "{table}"')
            schema_editor.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
            schema_editor.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')

    # These account/global tables had no prior tenant RLS policy before Phase 0.
    for table in ("audit_log", "accounts_user_session", "accounts_websocket_ticket", "accounts_login_attempt_log",
                  "notifications_sms_template", "notifications_preference", "search_saved_search"):
        if table in tables:
            schema_editor.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
            schema_editor.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')


class Migration(migrations.Migration):
    dependencies = [("settings", "0006_harden_rbac_rls_policies")]
    operations = [migrations.RunPython(apply_child_table_rls, reverse_child_table_rls)]
