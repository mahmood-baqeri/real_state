import hashlib
import hmac
import time
from typing import Optional
from uuid import UUID
from django.conf import settings
from apps.accounts.models import User
from apps.properties.models import Property
from apps.properties.services import list_agency_properties
from common.exceptions import NotFoundDomainError, PermissionDeniedDomainError
from common.permissions import (
    can_edit_property,
    get_active_membership,
    has_agency_permission,
    is_super_admin,
)


def is_property_publicly_publishable(prop: Property) -> bool:
    return (
        not prop.is_deleted
        and prop.status == Property.Status.PUBLISHED
        and prop.visibility == Property.Visibility.PUBLIC_PORTAL
    )


def assert_property_tenant_access(
    *,
    user: Optional[User],
    agency_id: Optional[UUID],
    property_id: UUID,
) -> Property:
    if not user or not user.is_authenticated:
        raise PermissionDeniedDomainError("برای دسترسی به مدیریت تور مجازی باید وارد شوید.")
    qs = list_agency_properties(user=user, agency_id=agency_id)
    prop = qs.filter(id=property_id).first()
    if not prop:
        if Property.objects.all_tenants().filter(id=property_id, is_deleted=False).exists():
            raise PermissionDeniedDomainError("شما به این ملک یا آژانس دسترسی ندارید.")
        raise NotFoundDomainError("ملک مورد نظر یافت نشد.")
    return prop


def assert_tour_view_access(
    *,
    user: Optional[User],
    agency_id: Optional[UUID],
    prop: Property,
) -> None:
    if not user or not user.is_authenticated:
        raise PermissionDeniedDomainError("احراز هویت برای مشاهده بخش مدیریتی تور الزامی است.")
    if is_super_admin(user):
        return
    if not agency_id or prop.agency_id != agency_id:
        raise PermissionDeniedDomainError("دسترسی غیرمجاز بین آژانس‌ها مسدود شد.")
    membership = get_active_membership(user, prop.agency_id)
    if not membership:
        raise PermissionDeniedDomainError("عضویت فعال در آژانس مالک ملک یافت نشد.")
    if has_agency_permission(user, prop.agency_id, "virtual_tour.view") or has_agency_permission(
        user, prop.agency_id, "property.view_all_agency"
    ):
        return
    if can_edit_property(user, prop):
        return
    if prop.visibility == Property.Visibility.PUBLIC_PORTAL:
        return
    raise PermissionDeniedDomainError("مجوز مشاهده تور مجازی این ملک را ندارید.")


def assert_tour_edit_access(
    *,
    user: Optional[User],
    agency_id: Optional[UUID],
    prop: Property,
) -> None:
    if not user or not user.is_authenticated:
        raise PermissionDeniedDomainError("برای ویرایش تور باید وارد حساب کاربری شوید.")
    if is_super_admin(user):
        return
    if not agency_id or prop.agency_id != agency_id:
        raise PermissionDeniedDomainError("عدم تطابق آژانس؛ ویرایش تور متعلق به آژانس دیگر مجاز نیست.")
    if has_agency_permission(user, prop.agency_id, "virtual_tour.edit"):
        return
    if can_edit_property(user, prop):
        return
    raise PermissionDeniedDomainError("مجوز ویرایش این تور مجازی را ندارید.")


def assert_tour_approve_access(
    *,
    user: Optional[User],
    agency_id: Optional[UUID],
    prop: Property,
) -> None:
    if not user or not user.is_authenticated:
        raise PermissionDeniedDomainError("برای تأیید کیفیت باید وارد شوید.")
    if is_super_admin(user):
        return
    if not agency_id or prop.agency_id != agency_id:
        raise PermissionDeniedDomainError("عدم دسترسی بین آژانسی.")
    membership = get_active_membership(user, prop.agency_id)
    if membership and membership.role.code in ("AGENCY_MANAGER", "BRANCH_MANAGER", "SALES_MANAGER"):
        return
    if has_agency_permission(user, prop.agency_id, "virtual_tour.approve") or has_agency_permission(
        user, prop.agency_id, "property.publish"
    ):
        return
    raise PermissionDeniedDomainError("فقط مدیران یا کاربران دارای مجوز تأیید می‌توانند پانوراما را تأیید یا رد کنند.")


def assert_tour_publish_access(
    *,
    user: Optional[User],
    agency_id: Optional[UUID],
    prop: Property,
) -> None:
    if not user or not user.is_authenticated:
        raise PermissionDeniedDomainError("برای انتشار تور باید وارد شوید.")
    if is_super_admin(user):
        return
    if not agency_id or prop.agency_id != agency_id:
        raise PermissionDeniedDomainError("عدم دسترسی بین آژانسی.")
    membership = get_active_membership(user, prop.agency_id)
    if membership and membership.role.code == "AGENCY_MANAGER":
        return
    if has_agency_permission(user, prop.agency_id, "virtual_tour.publish") or has_agency_permission(
        user, prop.agency_id, "property.publish"
    ):
        return
    raise PermissionDeniedDomainError("مجوز انتشار عمومی تور مجازی را ندارید.")


def _asset_signing_key() -> bytes:
    key = getattr(settings, "JWT_SIGNING_KEY", None) or settings.SECRET_KEY
    return f"vt-asset:{key}".encode("utf-8")


def sign_asset_access_token(
    *,
    kind: str,
    object_id: str,
    tour_id: str,
    ttl_seconds: int = 3600,
) -> str:
    exp = int(time.time()) + max(60, ttl_seconds)
    payload = f"{kind}:{object_id}:{tour_id}:{exp}"
    sig = hmac.new(_asset_signing_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def verify_asset_access_token(
    *,
    token: str,
    kind: str,
    object_id: str,
    tour_id: str,
) -> bool:
    if not token or "." not in token:
        return False
    try:
        exp_str, provided_sig = token.split(".", 1)
        exp = int(exp_str)
    except ValueError:
        return False
    if exp < int(time.time()):
        return False
    payload = f"{kind}:{object_id}:{tour_id}:{exp}"
    expected_sig = hmac.new(_asset_signing_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_sig, provided_sig)


def build_private_file_url(
    *,
    kind: str,
    object_id: str,
    tour_id: str,
    signed: bool = True,
) -> str:
    base = f"/api/v1/virtual-tours/files/{kind}/{object_id}"
    if signed:
        token = sign_asset_access_token(kind=kind, object_id=str(object_id), tour_id=str(tour_id))
        return f"{base}?token={token}"
    return base
