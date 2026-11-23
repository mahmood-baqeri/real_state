"""
Django Core foundational primitives (Multi-tenancy, RBAC permissions, Encryption,
Localization, Exceptions, and Idempotency) re-exported cleanly for domain apps.
"""
from common.exceptions import (
    AuthenticationDomainError,
    ConflictDomainError,
    DomainError,
    NotFoundDomainError,
    PermissionDeniedDomainError,
    ValidationDomainError,
)
from common.permissions import (
    can_edit_customer,
    can_edit_property,
    can_view_owner_pii,
    get_active_membership,
    get_agency_policy,
    get_effective_permissions,
    has_agency_permission,
    is_super_admin,
)
from common.tenant.context import get_current_agency_id, set_current_agency_id, tenant_bypass
from common.tenant.managers import TenantScopedManager

__all__ = [
    "AuthenticationDomainError",
    "ConflictDomainError",
    "DomainError",
    "NotFoundDomainError",
    "PermissionDeniedDomainError",
    "ValidationDomainError",
    "can_edit_customer",
    "can_edit_property",
    "can_view_owner_pii",
    "get_active_membership",
    "get_agency_policy",
    "get_current_agency_id",
    "get_effective_permissions",
    "has_agency_permission",
    "is_super_admin",
    "set_current_agency_id",
    "tenant_bypass",
    "TenantScopedManager",
]
