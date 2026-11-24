from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("payroll", "0001_initial")]
    operations = [
        migrations.AlterField(
            model_name="payslip",
            name="status",
            field=models.CharField(
                choices=[
                    ("DRAFT", "Draft"), ("APPROVED", "Approved"),
                    ("PAID", "Paid"), ("CANCELLED", "Cancelled"),
                ],
                default="DRAFT", max_length=16,
            ),
        ),
    ]
