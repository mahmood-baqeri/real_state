from django.db import migrations


def _policy_specs(apps):
    from common.tenant.rls import discover_tenant_relation_paths
    specs = []
    for model in apps.get_models():
        if model._meta.app_label == "accounts" or not model._meta.managed or model._meta.proxy:
            continue
        try:
            agency_field = model._meta.get_field("agency")
        except Exception:
            agency_field = None
        relation_paths = discover_tenant_relation_paths(model)
        if agency_field is not None:
            specs.append((model, agency_field, relation_paths, False, agency_field.null))
        elif relation_paths:
            specs.append((model, None, relation_paths, False, False))
    return specs


def enable_tenant_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    from common.tenant.rls import generate_rls_policy_sql, generate_related_rls_policy_sql
    tables = set(schema_editor.connection.introspection.table_names())
    for model, agency_field, relation_paths, allow_global, allow_related in _policy_specs(apps):
        table = model._meta.db_table
        if table not in tables:
            continue
        if agency_field is not None:
            sql = generate_rls_policy_sql(
                table,
                agency_field.column,
                relation_paths=relation_paths,
                allow_global_rows=allow_global,
                allow_related_rows=allow_related,
            )
        else:
            sql = generate_related_rls_policy_sql(table, relation_paths)
        schema_editor.execute(sql)

    if "accounts_agency_membership" in tables:
        schema_editor.execute('ALTER TABLE "accounts_agency_membership" ENABLE ROW LEVEL SECURITY')
        schema_editor.execute('DROP POLICY IF EXISTS "membership_select_self" ON "accounts_agency_membership"')
        schema_editor.execute('DROP POLICY IF EXISTS "membership_tenant_write" ON "accounts_agency_membership"')
        schema_editor.execute("""
            CREATE POLICY "membership_select_self" ON "accounts_agency_membership" FOR SELECT
            USING (
                current_setting('app.tenant_bypass', true) = 'on'
                OR "user_id"::text = NULLIF(current_setting('app.current_user_id', true), '')
                OR "agency_id"::text = NULLIF(current_setting('app.current_agency_id', true), '')
            )
        """)
        schema_editor.execute("""
            CREATE POLICY "membership_tenant_write" ON "accounts_agency_membership" FOR ALL
            USING (
                current_setting('app.tenant_bypass', true) = 'on'
                OR "agency_id"::text = NULLIF(current_setting('app.current_agency_id', true), '')
            )
            WITH CHECK (
                current_setting('app.tenant_bypass', true) = 'on'
                OR "agency_id"::text = NULLIF(current_setting('app.current_agency_id', true), '')
            )
        """)

    if "accounts_role" in tables:
        schema_editor.execute('ALTER TABLE "accounts_role" ENABLE ROW LEVEL SECURITY')
        schema_editor.execute('DROP POLICY IF EXISTS "role_visibility" ON "accounts_role"')
        schema_editor.execute('DROP POLICY IF EXISTS "role_tenant_write" ON "accounts_role"')
        schema_editor.execute("""
            CREATE POLICY "role_visibility" ON "accounts_role" FOR SELECT
            USING (
                current_setting('app.tenant_bypass', true) = 'on'
                OR "agency_id" IS NULL
                OR "agency_id"::text = NULLIF(current_setting('app.current_agency_id', true), '')
            )
        """)
        schema_editor.execute("""
            CREATE POLICY "role_tenant_write" ON "accounts_role" FOR ALL
            USING (
                current_setting('app.tenant_bypass', true) = 'on'
                OR "agency_id"::text = NULLIF(current_setting('app.current_agency_id', true), '')
            )
            WITH CHECK (
                current_setting('app.tenant_bypass', true) = 'on'
                OR "agency_id"::text = NULLIF(current_setting('app.current_agency_id', true), '')
            )
        """)

    if "accounts_role_permission" in tables:
        schema_editor.execute('ALTER TABLE "accounts_role_permission" ENABLE ROW LEVEL SECURITY')
        schema_editor.execute('DROP POLICY IF EXISTS "role_permission_visibility" ON "accounts_role_permission"')
        schema_editor.execute('DROP POLICY IF EXISTS "role_permission_write" ON "accounts_role_permission"')
        schema_editor.execute("""
            CREATE POLICY "role_permission_visibility" ON "accounts_role_permission" FOR SELECT
            USING (
                current_setting('app.tenant_bypass', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM "accounts_role" r
                    WHERE r."id" = "accounts_role_permission"."role_id"
                      AND (r."agency_id" IS NULL OR
                           r."agency_id"::text = NULLIF(current_setting('app.current_agency_id', true), ''))
                )
            )
        """)
        schema_editor.execute("""
            CREATE POLICY "role_permission_write" ON "accounts_role_permission" FOR ALL
            USING (
                current_setting('app.tenant_bypass', true) = 'on'
                OR EXISTS (SELECT 1 FROM "accounts_role" r WHERE r."id" = "accounts_role_permission"."role_id"
                           AND r."agency_id"::text = NULLIF(current_setting('app.current_agency_id', true), ''))
            )
            WITH CHECK (
                current_setting('app.tenant_bypass', true) = 'on'
                OR EXISTS (SELECT 1 FROM "accounts_role" r WHERE r."id" = "accounts_role_permission"."role_id"
                           AND r."agency_id"::text = NULLIF(current_setting('app.current_agency_id', true), ''))
            )
        """)

    if "accounts_membership_permission_override" in tables:
        schema_editor.execute('ALTER TABLE "accounts_membership_permission_override" ENABLE ROW LEVEL SECURITY')
        schema_editor.execute('DROP POLICY IF EXISTS "membership_override_visibility" ON "accounts_membership_permission_override"')
        schema_editor.execute('DROP POLICY IF EXISTS "membership_override_write" ON "accounts_membership_permission_override"')
        schema_editor.execute("""
            CREATE POLICY "membership_override_visibility" ON "accounts_membership_permission_override" FOR SELECT
            USING (
                current_setting('app.tenant_bypass', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM "accounts_agency_membership" m
                    WHERE m."id" = "accounts_membership_permission_override"."membership_id"
                      AND (
                          m."user_id"::text = NULLIF(current_setting('app.current_user_id', true), '')
                          OR m."agency_id"::text = NULLIF(current_setting('app.current_agency_id', true), '')
                      )
                )
            )
        """)
        schema_editor.execute("""
            CREATE POLICY "membership_override_write" ON "accounts_membership_permission_override" FOR ALL
            USING (
                current_setting('app.tenant_bypass', true) = 'on'
                OR EXISTS (SELECT 1 FROM "accounts_agency_membership" m
                           WHERE m."id" = "accounts_membership_permission_override"."membership_id"
                             AND m."agency_id"::text = NULLIF(current_setting('app.current_agency_id', true), ''))
            )
            WITH CHECK (
                current_setting('app.tenant_bypass', true) = 'on'
                OR EXISTS (SELECT 1 FROM "accounts_agency_membership" m
                           WHERE m."id" = "accounts_membership_permission_override"."membership_id"
                             AND m."agency_id"::text = NULLIF(current_setting('app.current_agency_id', true), ''))
            )
        """)


def disable_tenant_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    tables = set(schema_editor.connection.introspection.table_names())
    policies = {
        "accounts_agency_membership": ["membership_select_self", "membership_tenant_write"],
        "accounts_role": ["role_visibility", "role_tenant_write"],
        "accounts_role_permission": ["role_permission_visibility", "role_permission_write"],
        "accounts_membership_permission_override": ["membership_override_visibility", "membership_override_write"],
    }
    for table, names in policies.items():
        if table in tables:
            for name in names:
                schema_editor.execute(f'DROP POLICY IF EXISTS "{name}" ON "{table}"')
            schema_editor.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')

    for model, agency_field, relation_path, _allow_global, _allow_related in _policy_specs(apps):
        table = model._meta.db_table
        if table not in tables:
            continue
        policy = f"{table[:40]}_tenant_isolation"
        schema_editor.execute(f'DROP POLICY IF EXISTS "{policy}" ON "{table}"')
        schema_editor.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')


class Migration(migrations.Migration):
    dependencies = [
        ("accounting", "0003_initial"),
        ("accounts", "0004_websocketticket"),
        ("agencies", "0002_initial"),
        ("ai_assistant", "0002_aiinteractionlog_latency_ms_and_more"),
        ("appointments", "0002_initial"),
        ("audit", "0001_initial"),
        ("branches", "0001_initial"),
        ("cms", "0003_article_agency_article_ai_generated_article_ai_model_and_more"),
        ("commissions", "0002_initial"),
        ("complaints", "0001_initial"),
        ("contracts", "0003_contractamendment"),
        ("crm", "0002_initial"),
        ("customers", "0002_initial"),
        ("documents", "0002_document_deleted_at_document_deleted_by_and_more"),
        ("employees", "0001_initial"),
        ("leads", "0002_lead_deleted_at_lead_deleted_by_lead_is_deleted_and_more"),
        ("negotiations", "0002_negotiation_agreed_price_negotiation_asking_price_and_more"),
        ("notifications", "0003_smstemplate_smsdeliverylog"),
        ("payments", "0003_paymentgatewaytransaction_base_currency_code_and_more"),
        ("payroll", "0002_payroll_cancellation_states"),
        ("properties", "0004_propertyverification_propertyverificationhistory_and_more"),
        ("property_media", "0001_initial"),
        ("reports", "0001_initial"),
        ("search", "0002_savedview"),
        ("settings", "0003_calendarsystem_alter_country_options_and_more"),
        ("subscriptions", "0002_billing_cycle_terms"),
        ("support", "0001_initial"),
        ("surveys", "0002_alter_surveyquestion_question_type"),
        ("transactions", "0002_deal_base_currency_code_deal_exchange_rate_snapshot"),
        ("virtual_tours", "0003_scan_assets"),
    ]
    operations = [migrations.RunPython(enable_tenant_rls, disable_tenant_rls)]
