from django.db import models
from common.models import TenantScopedModel


class Branch(TenantScopedModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32)
    country = models.ForeignKey("settings.Country", on_delete=models.PROTECT, default="IR")
    province = models.CharField(max_length=80, blank=True, default="")
    city = models.CharField(max_length=80, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    phone = models.CharField(max_length=32, blank=True, default="")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    working_hours = models.JSONField(default=dict, blank=True)
    is_main = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "branches_branch"
        unique_together = ("agency", "code")

    def __str__(self) -> str:
        return f"{self.agency.name} - {self.name}"
