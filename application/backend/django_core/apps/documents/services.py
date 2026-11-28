"""کنترل دسترسی، ثبت و دریافت اسناد خصوصی آژانس."""

from typing import Optional
from uuid import UUID
from django.db import models, transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.audit.services import record_audit_event
from apps.properties.models import Property
from apps.customers.models import Customer
from apps.contracts.models import Contract
from common.exceptions import NotFoundDomainError, PermissionDeniedDomainError, ValidationDomainError
from common.permissions import get_active_membership, has_agency_permission, is_super_admin
from integrations.registry import get_storage_provider
from integrations.storage import validate_uploaded_file
from .models import Document, DocumentDownloadLog, DocumentVersion


def _require_document_permission(user: User, agency_id: UUID, permission: str) -> None:
    if not (is_super_admin(user) or has_agency_permission(user, agency_id, permission)):
        raise PermissionDeniedDomainError("مجوز لازم برای این عملیات روی سند را ندارید.")


def _validate_document_relations(*, user: User, agency_id: UUID, data: dict) -> None:
    """فعال بودن ملک و مشتری و محدودهٔ هر رابطهٔ سند را بررسی می‌کند."""
    property_id = data.get("property_id")
    customer_id = data.get("customer_id")
    contract_id = data.get("contract_id")
    prop = None
    customer = None
    contract = None
    if property_id is not None:
        prop = Property.objects.all_tenants().filter(id=property_id, agency_id=agency_id, is_deleted=False).first()
        if prop is None:
            raise ValidationDomainError("ملک انتخاب‌شده متعلق به آژانس فعال نیست.")
    if customer_id is not None:
        customer = Customer.objects.all_tenants().filter(id=customer_id, agency_id=agency_id, is_deleted=False).first()
        if customer is None:
            raise ValidationDomainError("مشتری انتخاب‌شده متعلق به آژانس فعال نیست.")
    if contract_id is not None:
        contract = Contract.objects.all_tenants().filter(id=contract_id, agency_id=agency_id).first()
        if contract is None:
            raise ValidationDomainError("قرارداد انتخاب‌شده متعلق به آژانس فعال نیست.")

    membership = get_active_membership(user, agency_id)
    if membership and membership.role.code == "REAL_ESTATE_AGENT":
        if prop is not None and not prop.agent_assignments.filter(membership=membership).exists():
            raise PermissionDeniedDomainError("ملک به این مشاور تخصیص داده نشده است.")
        if customer is not None and customer.assigned_membership_id != membership.id:
            raise PermissionDeniedDomainError("مشتری به این مشاور تخصیص داده نشده است.")
        if contract is not None and not (
            contract.property.agent_assignments.filter(membership=membership).exists()
            or contract.parties.filter(customer__assigned_membership=membership).exists()
        ):
            raise PermissionDeniedDomainError("قرارداد به پرونده‌های مجاز این مشاور مرتبط نیست.")
    elif membership and membership.role.code == "BRANCH_MANAGER":
        branch_id = membership.branch_id
        if prop is not None and (not branch_id or prop.branch_id != branch_id):
            raise PermissionDeniedDomainError("ملک خارج از شعبه فعال است.")
        if customer is not None and (
            not branch_id or customer.assigned_membership is None
            or customer.assigned_membership.branch_id != branch_id
        ):
            raise PermissionDeniedDomainError("مشتری خارج از شعبه فعال است.")
        if contract is not None and (
            not branch_id or contract.property.branch_id != branch_id
        ):
            raise PermissionDeniedDomainError("قرارداد خارج از شعبه فعال است.")

    access_level = data.get("access_level")
    if access_level and access_level not in Document.AccessLevel.values:
        raise ValidationDomainError("سطح دسترسی سند معتبر نیست.")


def list_documents(
    *,
    user: User,
    agency_id: Optional[UUID],
    category: Optional[str] = None,
    property_id: Optional[UUID] = None,
    customer_id: Optional[UUID] = None,
    contract_id: Optional[UUID] = None,
    q: Optional[str] = None,
):
    """سندهایی را برمی‌گرداند که کاربر مجوز دیدن تمام روابط آن‌ها را دارد."""
    qs = (
        Document.objects.all_tenants()
        .filter(is_deleted=False)
        .select_related("property", "customer", "contract", "agency")
        .prefetch_related("versions")
    )
    if agency_id:
        if not (is_super_admin(user) or get_active_membership(user, agency_id)):
            raise PermissionDeniedDomainError("عدم دسترسی به اسناد این آژانس.")
        _require_document_permission(user, agency_id, "document.view")
        qs = qs.filter(agency_id=agency_id)
        membership = get_active_membership(user, agency_id)
        if membership and membership.role.code == "REAL_ESTATE_AGENT":
            from django.db.models import Q
            contract_access = (
                Q(contract__property__agent_assignments__membership=membership)
                | Q(contract__parties__customer__assigned_membership=membership)
            )
            qs = qs.filter(
                (Q(property__isnull=True) | Q(property__agent_assignments__membership=membership))
                & (Q(customer__isnull=True) | Q(customer__assigned_membership=membership))
                & (Q(contract__isnull=True) | contract_access)
            ).filter(
                Q(created_by=user)
                | Q(property__agent_assignments__membership=membership)
                | Q(customer__assigned_membership=membership)
                | contract_access
            ).distinct()
        elif membership and membership.role.code == "BRANCH_MANAGER":
            from django.db.models import Q
            branch_id = membership.branch_id
            if branch_id:
                qs = qs.filter(
                    (Q(property__isnull=True) | Q(property__branch_id=branch_id))
                    & (Q(customer__isnull=True) | Q(customer__assigned_membership__branch_id=branch_id))
                    & (Q(contract__isnull=True) | Q(contract__property__branch_id=branch_id))
                ).filter(
                    Q(property__branch_id=branch_id)
                    | Q(customer__assigned_membership__branch_id=branch_id)
                    | Q(contract__property__branch_id=branch_id)
                    | Q(property__isnull=True, customer__isnull=True, contract__isnull=True, created_by=user)
                ).distinct()
            else:
                qs = qs.filter(property__isnull=True, customer__isnull=True, contract__isnull=True, created_by=user)
        if not (
            is_super_admin(user)
            or has_agency_permission(user, agency_id, "document.manage_access")
        ):
            qs = qs.exclude(access_level=Document.AccessLevel.CONFIDENTIAL)
    else:
        if not is_super_admin(user):
            raise PermissionDeniedDomainError("ابتدا آژانس را انتخاب کنید.")

    if category:
        qs = qs.filter(category=category)
    if property_id:
        qs = qs.filter(property_id=property_id)
    if customer_id:
        qs = qs.filter(customer_id=customer_id)
    if contract_id:
        qs = qs.filter(contract_id=contract_id)
    if q:
        qs = qs.filter(models.Q(title__icontains=q) | models.Q(category__icontains=q))
    return qs.order_by("-created_at")


def _resolve_document(*, user: User, agency_id: Optional[UUID], document_id: UUID) -> Document:
    doc = list_documents(user=user, agency_id=agency_id).filter(id=document_id).first()
    if not doc:
        raise NotFoundDomainError("سند یافت نشد یا مجاز به مشاهده آن نیستید.")
    return doc


@transaction.atomic
def create_document(*, user: User, agency_id: Optional[UUID], data: dict) -> Document:
    if not agency_id:
        raise ValidationDomainError("ابتدا آژانس فعال را انتخاب کنید.")
    membership = get_active_membership(user, agency_id)
    if not membership and not is_super_admin(user):
        raise PermissionDeniedDomainError("عضو فعال آژانس نیستید.")
    _require_document_permission(user, agency_id, "document.upload")
    _validate_document_relations(user=user, agency_id=agency_id, data=data)
    doc = Document.objects.all_tenants().create(
        agency_id=agency_id,
        title=data["title"].strip(),
        category=data.get("category", "GENERAL"),
        access_level=data.get("access_level", Document.AccessLevel.AGENCY_INTERNAL),
        property_id=data.get("property_id"),
        customer_id=data.get("customer_id"),
        contract_id=data.get("contract_id"),
        created_by=user,
    )
    DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        file_key=f"private/pending/{doc.id}/v1",
        mime_type=data.get("mime_type", "application/pdf"),
        file_size_bytes=int(data.get("file_size_bytes", 1024)),
        created_by=user,
    )
    record_audit_event(
        action="DOCUMENT_UPLOADED",
        resource_type="Document",
        resource_id=str(doc.id),
        actor=user,
        agency_id=agency_id,
    )
    return doc


@transaction.atomic
def upload_document_file(
    *,
    user: User,
    agency_id: Optional[UUID],
    title: str,
    category: str,
    access_level: str,
    filename: str,
    content_type: str,
    content: bytes,
    property_id: Optional[UUID] = None,
    customer_id: Optional[UUID] = None,
    contract_id: Optional[UUID] = None,
) -> Document:
    if not agency_id:
        raise ValidationDomainError("ابتدا آژانس فعال را انتخاب کنید.")
    membership = get_active_membership(user, agency_id)
    if not membership and not is_super_admin(user):
        raise PermissionDeniedDomainError("عضو فعال آژانس نیستید.")
    _require_document_permission(user, agency_id, "document.upload")
    _validate_document_relations(
        user=user,
        agency_id=agency_id,
        data={"property_id": property_id, "customer_id": customer_id, "contract_id": contract_id, "access_level": access_level},
    )
    safe_name, verified_mime = validate_uploaded_file(
        filename=filename, content_type=content_type, content=content
    )
    storage = get_storage_provider()
    stored = storage.put_bytes(
        key_prefix=f"private/agencies/{agency_id}/documents",
        safe_filename=safe_name,
        content=content,
        mime_type=verified_mime,
    )
    doc = Document.objects.all_tenants().create(
        agency_id=agency_id,
        title=title.strip() or safe_name,
        category=category or "GENERAL",
        access_level=access_level or Document.AccessLevel.AGENCY_INTERNAL,
        property_id=property_id,
        customer_id=customer_id,
        contract_id=contract_id,
        created_by=user,
    )
    DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        file_key=stored.file_key,
        mime_type=stored.mime_type,
        file_size_bytes=stored.size_bytes,
        created_by=user,
    )
    record_audit_event(
        action="DOCUMENT_FILE_UPLOADED",
        resource_type="Document",
        resource_id=str(doc.id),
        actor=user,
        agency_id=agency_id,
        after_state={"file_key": stored.file_key, "mime": stored.mime_type, "bytes": stored.size_bytes},
    )
    return doc


@transaction.atomic
def update_document(*, user: User, agency_id: Optional[UUID], document_id: UUID, data: dict) -> Document:
    doc = _resolve_document(user=user, agency_id=agency_id, document_id=document_id)
    _require_document_permission(user, doc.agency_id, "document.edit")
    _validate_document_relations(user=user, agency_id=doc.agency_id, data=data)
    if "access_level" in data and data["access_level"] != doc.access_level:
        _require_document_permission(user, doc.agency_id, "document.manage_access")
    for k in ("title", "category", "access_level", "property_id", "customer_id", "contract_id"):
        if k in data:
            val = data[k]
            if k == "title" and isinstance(val, str):
                val = val.strip()
                if not val:
                    raise ValidationDomainError("عنوان سند نمی‌تواند خالی باشد.")
            setattr(doc, k, val)
    doc.updated_by = user
    doc.save()
    record_audit_event(
        action="DOCUMENT_UPDATED",
        resource_type="Document",
        resource_id=str(doc.id),
        actor=user,
        agency_id=doc.agency_id,
    )
    return doc


@transaction.atomic
def soft_delete_document(*, user: User, agency_id: Optional[UUID], document_id: UUID) -> Document:
    doc = _resolve_document(user=user, agency_id=agency_id, document_id=document_id)
    _require_document_permission(user, doc.agency_id, "document.delete")
    doc.is_deleted = True
    doc.deleted_at = timezone.now()
    doc.deleted_by = user
    doc.updated_by = user
    doc.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_by", "updated_at"])
    record_audit_event(
        action="DOCUMENT_ARCHIVED",
        resource_type="Document",
        resource_id=str(doc.id),
        actor=user,
        agency_id=doc.agency_id,
    )
    return doc


@transaction.atomic
def log_document_download(*, user: User, agency_id: Optional[UUID], document_id: UUID, ip_address: Optional[str] = None) -> Document:
    doc = _resolve_document(user=user, agency_id=agency_id, document_id=document_id)
    _require_document_permission(user, doc.agency_id, "document.download")
    DocumentDownloadLog.objects.create(document=doc, user=user, ip_address=ip_address, created_by=user)
    return doc
