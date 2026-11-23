from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0001_initial")]
    operations = [
        migrations.AlterField(
            model_name="agencysubscription",
            name="billing_cycle",
            field=models.CharField(choices=[("MONTH_1", "1 month"), ("MONTH_2", "2 months"), ("MONTH_3", "3 months"), ("MONTH_6", "6 months"), ("MONTH_12", "12 months"), ("MONTHLY", "Legacy monthly"), ("ANNUAL", "Legacy annual")], default="MONTH_1", max_length=16),
        ),
    ]
