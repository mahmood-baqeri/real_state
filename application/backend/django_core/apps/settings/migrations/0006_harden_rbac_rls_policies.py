from django.db import migrations


def apply_policies(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    tables = set(schema_editor.connection.introspection.table_names())
    if "accounts_role_permission" in tables:
        schema_editor.execute('DROP POLICY IF EXISTS "role_permission_visibility" ON "accounts_role_permission"')
        schema_editor.execute('DROP POLICY IF EXISTS "role_permission_write" ON "accounts_role_permission"')
        schema_editor.execute("""
            CREATE POLICY "role_permission_visibility" ON "accounts_role_permission" FOR SELECT
            USING (current_setting('app.tenant_bypass', true) = 'on' OR EXISTS (
                SELECT 1 FROM "accounts_role" r
                WHERE r."id" = "accounts_role_permission"."role_id"
                  AND (r."agency_id" IS NULL OR r."agency_id"::text = NULLIF(current_setting('app.current_agency_id', true), ''))
            ))
        """)
        schema_editor.execute("""
            CREATE POLICY "role_permission_write" ON "accounts_role_permission" FOR ALL
            USING (current_setting('app.tenant_bypass', true) = 'on' OR EXISTS (
                SELECT 1 FROM "accounts_role" r
                WHERE r."id" = "accounts_role_permission"."role_id"
                  AND r."agency_id"::text = NULLIF(current_setting('app.current_agency_id', true), '')
            ))
            WITH CHECK (current_setting('app.tenant_bypass', true) = 'on' OR EXISTS (
                SELECT 1 FROM "accounts_role" r
                WHERE r."id" = "accounts_role_permission"."role_id"
                  AND r."agency_id"::text = NULLIF(current_setting('app.current_agency_id', true), '')
            ))
        """)
    if "accounts_membership_permission_override" in tables:
        schema_editor.execute('DROP POLICY IF EXISTS "membership_override_visibility" ON "accounts_membership_permission_override"')
        schema_editor.execute('DROP POLICY IF EXISTS "membership_override_write" ON "accounts_membership_permission_override"')
        schema_editor.execute("""
            CREATE POLICY "membership_override_visibility" ON "accounts_membership_permission_override" FOR SELECT
            USING (current_setting('app.tenant_bypass', true) = 'on' OR EXISTS (
                SELECT 1 FROM "accounts_agency_membership" m
                WHERE m."id" = "accounts_membership_permission_override"."membership_id"
                  AND (m."user_id"::text = NULLIF(current_setting('app.current_user_id', true), '')
                       OR m."agency_id"::text = NULLIF(current_setting('app.current_agency_id', true), ''))
            ))
        """)
        schema_editor.execute("""
            CREATE POLICY "membership_override_write" ON "accounts_membership_permission_override" FOR ALL
            USING (current_setting('app.tenant_bypass', true) = 'on' OR EXISTS (
                SELECT 1 FROM "accounts_agency_membership" m
                WHERE m."id" = "accounts_membership_permission_override"."membership_id"
                  AND m."agency_id"::text = NULLIF(current_setting('app.current_agency_id', true), '')
            ))
            WITH CHECK (current_setting('app.tenant_bypass', true) = 'on' OR EXISTS (
                SELECT 1 FROM "accounts_agency_membership" m
                WHERE m."id" = "accounts_membership_permission_override"."membership_id"
                  AND m."agency_id"::text = NULLIF(current_setting('app.current_agency_id', true), '')
            ))
        """)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("settings", "0005_force_tenant_rls")]
    operations = [migrations.RunPython(apply_policies, noop_reverse)]
