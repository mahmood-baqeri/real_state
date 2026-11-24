import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_initial'),
        ('customers', '0002_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='CustomerTransfer',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(db_index=True, default=timezone.now, editable=False)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reason', models.CharField(max_length=500)),
                ('transferred_at', models.DateTimeField(db_index=True, default=timezone.now)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transfer_history', to='customers.customer')),
                ('from_membership', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='customer_transfers_from', to='accounts.agencymembership')),
                ('to_membership', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='customer_transfers_to', to='accounts.agencymembership')),
            ],
            options={'db_table': 'customers_transfer_history', 'ordering': ['-transferred_at']},
        )
    ]
