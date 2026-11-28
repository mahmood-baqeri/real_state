"""اجرای RLS را برای مالک جدول در جدول‌های مستأجر با آژانس اختیاری اجباری می‌کند."""

from django.db import migrations


TABLES = (
    "settings_provider_configuration",
    "settings_system_setting",
    "contracts_template",
    "payments_gateway_transaction",
    "support_canned_reply",
    "surveys_survey",
    "cms_article",
)


def force_rls(apps, schema_editor):
    """وضعیت FORCE را روی جدول‌هایی که سیاست مستأجر دارند فعال می‌کند."""
    if schema_editor.connection.vendor == "postgresql":
        for table in TABLES:
            schema_editor.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')


def reverse_force_rls(apps, schema_editor):
    """وضعیت FORCE پیش از این مهاجرت را بازمی‌گرداند."""
    if schema_editor.connection.vendor == "postgresql":
        for table in TABLES:
            schema_editor.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')


class Migration(migrations.Migration):
    """سیاست‌های موجود را حفظ و اجرای آن‌ها را اجباری می‌کند."""

    dependencies = [("settings", "0007_rls_child_tables")]
    operations = [migrations.RunPython(force_rls, reverse_force_rls)]
