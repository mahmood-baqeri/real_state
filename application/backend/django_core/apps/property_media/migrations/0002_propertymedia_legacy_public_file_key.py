from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("property_media", "0001_initial")]
    operations = [migrations.AddField(
        model_name="propertymedia", name="legacy_public_file_key",
        field=models.CharField(blank=True, default="", max_length=255),
    )]
