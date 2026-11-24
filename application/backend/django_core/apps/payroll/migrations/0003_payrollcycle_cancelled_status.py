from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("payroll", "0002_payroll_cancellation_states")]
    operations = [
        migrations.AlterField(
            model_name="payrollcycle", name="status",
            field=models.CharField(choices=[("OPEN", "Open"), ("CALCULATED", "Calculated"), ("APPROVED", "Approved"), ("PAID", "Paid"), ("CANCELLED", "Cancelled")], default="OPEN", max_length=16),
        ),
    ]
