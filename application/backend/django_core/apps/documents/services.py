from typing import Optional
from uuid import UUID
from django.db import transaction
from apps.accounts.models import User
from apps.audit.services import record_audit_event
from common.exceptions import NotFoundDomainError, PermissionDeniedDomainError
from common.permissions import get_active_membership, has_agency_permission, is_super_admin
from integrations.registry import get_storage_provider
from integrations.storage import validate_uploaded_file
from .models import Document, DocumentDownloadLog, DocumentVersion


def list_documents(*, user: User, agency_id: UUID, category: Optional[str] = None):
    if not (is_super_admin(user) or get_active_membership(user, agency_id)):
        raise PermissionDeniedDomainError("عدم دسترسی به اسناد این آژانس.")
    qs = (
        Document.objects.all_tenants()
        .filter(agency_id=agency_id)
        .select_related("property", "customer", "contract")
        .prefetch_related("versions")
    )
    if not (
        is_super_admin(user)
        or has_agency_permission(user, agency_id, "accounting.view")
        or has_agency_permission(user, agency_id, "deal.view_all_agency")
    ):
        qs = qs.exclude(access_level=Document.AccessLevel.CONFIDENTIAL)
    if category:
        qs = qs.filter(category=category)
    return qs.order_by("-created_at")


@transaction.atomic
def create_document(*, user: User, agency_id: UUID, data: dict) -> Document:
    membership = get_active_membership(user, agency_id)
    if not membership and not is_super_admin(user):
        raise PermissionDeniedDomainError("عضو فعال آژانس نیستید.")
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
        file_key=data.get("file_key", f"docs/{doc.id}/v1.pdf"),
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
    agency_id: UUID,
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
    membership = get_active_membership(user, agency_id)
    if not membership and not is_super_admin(user):
        raise PermissionDeniedDomainError("عضو فعال آژانس نیستید.")
    safe_name, verified_mime = validate_uploaded_file(
        filename=filename, content_type=content_type, content=content
    )
    storage = get_storage_provider()
    stored = storage.put_bytes(
        key_prefix=f"agencies/{agency_id}/documents",
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
def log_document_download(*, user: User, agency_id: UUID, document_id: UUID, ip_address: Optional[str] = None) -> Document:
    doc = list_documents(user=user, agency_id=agency_id).filter(id=document_id).first()
    if not doc:
        raise NotFoundDomainError("سند یافت نشد یا مجاز به مشاهده آن نیستید.")
    DocumentDownloadLog.objects.create(document=doc, user=user, ip_address=ip_address, created_by=user)
    return doc
