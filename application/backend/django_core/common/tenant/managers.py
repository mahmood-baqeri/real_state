from django.db import models
from django.core.exceptions import PermissionDenied
from .context import get_current_agency_id, is_tenant_bypassed


class TenantScopedQuerySet(models.QuerySet):
    def active_only(self):
        if hasattr(self.model, "is_deleted"):
            return self.filter(is_deleted=False)
        return self


class TenantScopedManager(models.Manager):
    """Automatically scopes queries to the active agency_id unless explicitly bypassed."""

    def get_queryset(self) -> TenantScopedQuerySet:
        qs = TenantScopedQuerySet(self.model, using=self._db)
        if hasattr(self.model, "is_deleted"):
            qs = qs.filter(is_deleted=False)
        if not is_tenant_bypassed():
            agency_id = get_current_agency_id()
            if agency_id is None:
                # Missing tenant context must never silently become an all-tenant query.
                raise PermissionDenied("Tenant context is required for tenant-scoped queries.")
            qs = qs.filter(agency_id=agency_id)
        return qs

    def all_tenants(self) -> TenantScopedQuerySet:
        """Explicit escape hatch for SuperAdmin / Public Catalog / Cross-agency MLS."""
        return TenantScopedQuerySet(self.model, using=self._db)
