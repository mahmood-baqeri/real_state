"""کلید جلوگیری از تکرار را در محدودهٔ آژانس یکتا می‌کند."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """مسیر اصلی درگاه را برای تکرار درخواست ذخیره می‌کند."""

    dependencies = [("payments", "0003_paymentgatewaytransaction_base_currency_code_and_more")]

    operations = [
        migrations.AddField(
            model_name="paymentgatewaytransaction",
            name="redirect_url",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="paymentgatewaytransaction",
            name="idempotency_key",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddConstraint(
            model_name="paymentgatewaytransaction",
            constraint=models.UniqueConstraint(
                fields=("agency", "idempotency_key"),
                name="uq_payment_agency_idempotency",
            ),
        ),
    ]
