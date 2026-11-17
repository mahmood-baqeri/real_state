from typing import Optional
from apps.accounts.models import AgencyMembership, User
from apps.agencies.models import AgencyAccessPolicy


def is_super_admin(user: Optional[User]) -> bool:
    return bool(
        user
        and user.is_authenticated
        and (user.is_superuser or user.platform_role == User.PlatformRole.SUPER_ADMIN)
    )


def get_active_membership(user: Optional[User], agency_id) -> Optional[AgencyMembership]:
    if not user or not user.is_authenticated or not agency_id:
        return None
    return (
        AgencyMembership.objects.select_related("role", "agency", "branch")
        .prefetch_related("role__permissions", "permission_overrides")
        .filter(user=user, agency_id=agency_id, status=AgencyMembership.Status.ACTIVE)
        .first()
    )


def get_effective_permissions(user: Optional[User], agency_id) -> list[str]:
    if not user or not user.is_authenticated:
        return []
    if is_super_admin(user):
        return ["*"]
    membership = get_active_membership(user, agency_id)
    if membership is None:
        return []
    if membership.role.code == "AGENCY_MANAGER":
        return ["*"]
    codes = set(membership.role.permissions.values_list("code", flat=True))
    for ov in membership.permission_overrides.all():
        if ov.effect == "ALLOW":
            codes.add(ov.permission_id)
        elif ov.effect == "DENY":
            codes.discard(ov.permission_id)
    return sorted(codes)


def has_agency_permission(user: Optional[User], agency_id, permission_code: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    if is_super_admin(user):
        return True
    membership = get_active_membership(user, agency_id)
    if membership is None:
        return False
    if membership.role.code == "AGENCY_MANAGER":
        return True

    override = membership.permission_overrides.filter(permission_id=permission_code).first()
    if override is not None:
        return override.effect == "ALLOW"

    return membership.role.permissions.filter(code=permission_code).exists()


def get_agency_policy(agency_id) -> Optional[AgencyAccessPolicy]:
    if not agency_id:
        return None
    policy, _ = AgencyAccessPolicy.objects.get_or_create(agency_id=agency_id)
    return policy


def can_view_owner_pii(user: User, agency_id, is_assigned_agent: bool) -> bool:
    if is_super_admin(user):
        return True
    membership = get_active_membership(user, agency_id)
    if membership is None:
        return False
    if membership.role.code == "AGENCY_MANAGER":
        return True
    policy = get_agency_policy(agency_id)
    if policy.owner_pii_visibility == AgencyAccessPolicy.OwnerPIIVisibility.MANAGERS_ONLY:
        return has_agency_permission(user, agency_id, "owner.view_pii")
    if policy.owner_pii_visibility == AgencyAccessPolicy.OwnerPIIVisibility.ASSIGNED_AND_MANAGER:
        return is_assigned_agent or has_agency_permission(user, agency_id, "owner.view_pii")
    return has_agency_permission(user, agency_id, "owner.view_pii")


def can_edit_property(user: User, prop) -> bool:
    if is_super_admin(user):
        return True
    membership = get_active_membership(user, prop.agency_id)
    if not membership:
        return False
    if membership.role.code == "AGENCY_MANAGER" or has_agency_permission(
        user, prop.agency_id, "property.edit_all_agency"
    ):
        return True
    policy = get_agency_policy(prop.agency_id)
    is_assigned = prop.agent_assignments.filter(membership=membership).exists() or prop.created_by_id == user.id
    if policy.property_edit_scope == AgencyAccessPolicy.PropertyEditScope.ASSIGNED_ONLY:
        return is_assigned
    if policy.property_edit_scope == AgencyAccessPolicy.PropertyEditScope.BRANCH:
        return is_assigned or (membership.branch_id is not None and prop.branch_id == membership.branch_id)
    return is_assigned or has_agency_permission(user, prop.agency_id, "property.edit_all_agency")


def can_edit_customer(user: User, customer) -> bool:
    if is_super_admin(user):
        return True
    membership = get_active_membership(user, customer.agency_id)
    if not membership:
        return False
    if membership.role.code == "AGENCY_MANAGER" or has_agency_permission(
        user, customer.agency_id, "customer.edit_all_agency"
    ):
        return True
    policy = get_agency_policy(customer.agency_id)
    is_assigned = customer.assigned_membership_id == membership.id
    if policy.customer_edit_scope == AgencyAccessPolicy.CustomerEditScope.ASSIGNED_ONLY:
        return is_assigned
    if policy.customer_edit_scope == AgencyAccessPolicy.CustomerEditScope.SHARED_EDITORS:
        return is_assigned or customer.shares.filter(membership=membership, access_level="EDIT").exists()
    return is_assigned or has_agency_permission(user, customer.agency_id, "customer.edit_all_agency")
