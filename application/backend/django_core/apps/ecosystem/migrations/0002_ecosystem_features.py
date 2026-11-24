# Generated for Ecosystem feature completion.
import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("ecosystem", "0001_initial"),
        ("agencies", "0002_initial"),
        ("properties", "0004_propertyverification_propertyverificationhistory_and_more"),
        ("contracts", "0003_contractamendment"),
        ("customers", "0003_customertransfer"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CooperationPropertyShare",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("consented_at", models.DateTimeField()),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ecosystem_cooperationpropertyshare_created", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ecosystem_cooperationpropertyshare_updated", to=settings.AUTH_USER_MODEL)),
                ("shared_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ecosystem_shared_properties", to=settings.AUTH_USER_MODEL)),
                ("cooperation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="property_shares", to="agencies.agencycooperation")),
                ("property", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cooperation_shares", to="properties.property")),
            ],
            options={"db_table": "ecosystem_cooperation_property_share"},
        ),
        migrations.AddConstraint(
            model_name="cooperationpropertyshare",
            constraint=models.UniqueConstraint(fields=("cooperation", "property"), name="uq_ecosystem_coop_property"),
        ),
        migrations.CreateModel(
            name="CooperationSettlement",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=20)),
                ("currency_code", models.CharField(max_length=10)),
                ("split_percent", models.DecimalField(decimal_places=2, max_digits=6)),
                ("status", models.CharField(choices=[("DRAFT","پیش‌نویس"),("PENDING_APPROVAL","در انتظار تأیید"),("APPROVED","تأییدشده"),("PAID","پرداخت‌شده"),("CANCELLED","لغوشده")], db_index=True, default="DRAFT", max_length=20)),
                ("description", models.CharField(blank=True, default="", max_length=300)),
                ("external_reference", models.CharField(blank=True, default="", max_length=120)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ecosystem_approved_settlements", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ecosystem_cooperationsettlement_created", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ecosystem_cooperationsettlement_updated", to=settings.AUTH_USER_MODEL)),
                ("cooperation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="settlements", to="agencies.agencycooperation")),
                ("contract", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="cooperation_settlements", to="contracts.contract")),
                ("payer_agency", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cooperation_payables", to="agencies.agency")),
                ("payee_agency", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cooperation_receivables", to="agencies.agency")),
            ],
            options={"db_table": "ecosystem_cooperation_settlement", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="cooperationsettlement",
            constraint=models.CheckConstraint(check=models.Q(("amount__gt", 0)), name="ck_ecosystem_settlement_amount_positive"),
        ),
        migrations.AddConstraint(
            model_name="cooperationsettlement",
            constraint=models.CheckConstraint(check=models.Q(("split_percent__gte", 0), ("split_percent__lte", 100)), name="ck_ecosystem_settlement_split_range"),
        ),
        migrations.CreateModel(
            name="TrustScoreSnapshot",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("score", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("methodology_version", models.CharField(default="1.0", max_length=24)),
                ("components", models.JSONField(blank=True, default=dict)),
                ("evidence", models.JSONField(blank=True, default=dict)),
                ("coverage", models.PositiveSmallIntegerField(default=0)),
                ("is_public", models.BooleanField(default=False)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ecosystem_trustscoresnapshot_created", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ecosystem_trustscoresnapshot_updated", to=settings.AUTH_USER_MODEL)),
                ("agency", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="trust_score_snapshots", to="agencies.agency")),
            ],
            options={"db_table": "ecosystem_trust_score_snapshot", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="trustscoresnapshot",
            index=models.Index(fields=["agency", "-created_at"], name="ecosystem_trust_agency_created_idx"),
        ),
        migrations.CreateModel(
            name="OwnerReportSnapshot",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("period_start", models.DateField()),
                ("period_end", models.DateField()),
                ("report_data", models.JSONField(blank=True, default=dict)),
                ("generated_at", models.DateTimeField()),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ecosystem_ownerreportsnapshot_created", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ecosystem_ownerreportsnapshot_updated", to=settings.AUTH_USER_MODEL)),
                ("generated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ecosystem_owner_reports", to=settings.AUTH_USER_MODEL)),
                ("agency", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="owner_reports", to="agencies.agency")),
                ("owner_customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="owner_reports", to="customers.customer")),
            ],
            options={"db_table": "ecosystem_owner_report_snapshot", "ordering": ["-generated_at"]},
        ),
        migrations.AddConstraint(
            model_name="ownerreportsnapshot",
            constraint=models.UniqueConstraint(fields=("agency", "owner_customer", "period_start", "period_end"), name="uq_ecosystem_owner_report_period"),
        ),
    ]
