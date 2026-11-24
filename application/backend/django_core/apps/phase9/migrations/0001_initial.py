import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models
import django.utils.timezone

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("agencies", "0002_initial"),
        ("customers", "0003_customertransfer"),
        ("accounts", "0004_websocketticket"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(name="AfterDealCase", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now, editable=False)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("description", models.TextField(blank=True, default="")),
            ("contract_id", models.UUIDField(blank=True, db_index=True, null=True)),
            ("title", models.CharField(max_length=180)),
            ("category", models.CharField(default="GENERAL", max_length=40)),
            ("status", models.CharField(choices=[("OPEN", "باز"), ("IN_PROGRESS", "در حال پیگیری"), ("WAITING", "در انتظار پاسخ"), ("RESOLVED", "حل‌شده"), ("CANCELLED", "لغوشده")], db_index=True, default="OPEN", max_length=20)),
            ("priority", models.CharField(choices=[("LOW", "عادی"), ("MEDIUM", "متوسط"), ("HIGH", "زیاد"), ("URGENT", "فوری")], default="MEDIUM", max_length=12)),
            ("due_at", models.DateTimeField(blank=True, db_index=True, null=True)),
            ("resolved_at", models.DateTimeField(blank=True, null=True)),
            ("agency", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="after_deal_cases", to="agencies.agency")),
            ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="after_deal_cases", to="customers.customer")),
            ("assigned_membership", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="accounts.agencymembership")),
            ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="phase9_afterdealcase_created", to=settings.AUTH_USER_MODEL)),
            ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="phase9_afterdealcase_updated", to=settings.AUTH_USER_MODEL)),
        ], options={"db_table":"phase9_after_deal_case", "ordering":["-created_at"]}),
        migrations.CreateModel(name="AfterDealUpdate", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now, editable=False)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("body", models.TextField()), ("status_from", models.CharField(blank=True, default="", max_length=20)),
            ("status_to", models.CharField(blank=True, default="", max_length=20)),
            ("case", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="updates", to="phase9.afterdealcase")),
            ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="phase9_afterdealupdate_created", to=settings.AUTH_USER_MODEL)),
            ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="phase9_afterdealupdate_updated", to=settings.AUTH_USER_MODEL)),
        ], options={"db_table":"phase9_after_deal_update", "ordering":["-created_at"]}),
    ]
