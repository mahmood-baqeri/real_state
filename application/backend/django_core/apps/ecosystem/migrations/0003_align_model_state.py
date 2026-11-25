"""وضعیت مهاجرت مدل‌های اکوسیستم را با تعریف فعلی Django همگام می‌کند."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """نام ایندکس و روابط معکوس کاربران را همگام می‌کند."""

    dependencies = [
        ('ecosystem', '0002_ecosystem_features'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='trustscoresnapshot',
            new_name='ecosystem_t_agency__77bb6c_idx',
            old_name='ecosystem_trust_agency_created_idx',
        ),
        migrations.AlterField(
            model_name='afterdealcase',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='afterdealcase',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='afterdealupdate',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='afterdealupdate',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='cooperationpropertyshare',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='cooperationpropertyshare',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='cooperationsettlement',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='cooperationsettlement',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='ownerreportsnapshot',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='ownerreportsnapshot',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='trustscoresnapshot',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='trustscoresnapshot',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL),
        ),
    ]
