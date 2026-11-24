from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("documents", "0002_document_deleted_at_document_deleted_by_and_more")]
    operations = [migrations.AddField(
        model_name="documentversion", name="legacy_public_file_key",
        field=models.CharField(blank=True, default="", max_length=255),
    )]
