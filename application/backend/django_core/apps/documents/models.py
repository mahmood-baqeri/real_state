from django.conf import settings
from django.db import models
from common.models import BaseModel, TenantScopedModel


class Document(TenantScopedModel):
    class AccessLevel(models.TextChoices):
        PUBLIC = "PUBLIC", "Public"
        AGENCY_INTERNAL = "AGENCY_INTERNAL", "Agency Internal"
        CONFIDENTIAL = "CONFIDENTIAL", "Confidential (Contract/Finance)"

    title = models.CharField(max_length=160)
    category = models.CharField(max_length=64, default="GENERAL")
    access_level = models.CharField(
        max_length=24, choices=AccessLevel.choices, default=AccessLevel.AGENCY_INTERNAL
    )
    property = models.ForeignKey(
        "properties.Property", null=True, blank=True, on_delete=models.SET_NULL
    )
    customer = models.ForeignKey(
        "customers.Customer", null=True, blank=True, on_delete=models.SET_NULL
    )
    contract = models.ForeignKey(
        "contracts.Contract", null=True, blank=True, on_delete=models.SET_NULL
    )
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "documents_document"


class DocumentVersion(BaseModel):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    file_key = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=80)
    file_size_bytes = models.BigIntegerField()

    class Meta:
        db_table = "documents_version"
        unique_together = ("document", "version_number")


class DocumentDownloadLog(BaseModel):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="downloads")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "documents_download_log"
