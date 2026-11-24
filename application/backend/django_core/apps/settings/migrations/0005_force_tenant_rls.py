from django.db import migrations


def force_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    tables = set(schema_editor.connection.introspection.table_names())
    for model in apps.get_models():
        if not model._meta.managed:
            continue
        table = model._meta.db_table
        if table not in tables:
            continue
        try:
            agency_field = model._meta.get_field("agency")
        except Exception:
            continue
        if not agency_field.null:
            schema_editor.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            schema_editor.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
    for table in (
        "accounts_agency_membership", "accounts_role",
        "accounts_role_permission", "accounts_membership_permission_override",
    ):
        if table in tables:
            schema_editor.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            schema_editor.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')


def unforce_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    tables = set(schema_editor.connection.introspection.table_names())
    for model in apps.get_models():
        if not model._meta.managed:
            continue
        table = model._meta.db_table
        if table not in tables:
            continue
        try:
            agency_field = model._meta.get_field("agency")
        except Exception:
            continue
        if not agency_field.null:
            schema_editor.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
    for table in (
        "accounts_agency_membership", "accounts_role",
        "accounts_role_permission", "accounts_membership_permission_override",
    ):
        if table in tables:
            schema_editor.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')


class Migration(migrations.Migration):
    dependencies = [
        ("settings", "0004_enable_tenant_rls"),
        ("documents", "0003_documentversion_legacy_public_file_key"),
        ("property_media", "0002_propertymedia_legacy_public_file_key"),
        ("payroll", "0003_payrollcycle_cancelled_status"),
    ]
    operations = [migrations.RunPython(force_rls, unforce_rls)]
