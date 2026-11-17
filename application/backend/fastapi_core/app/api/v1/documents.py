from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, require_agency_context
from app.schemas.common import ok

router = APIRouter(prefix="/documents", tags=["Documents & Files"])


class DocumentCreateBody(BaseModel):
    title: str
    category: str = "GENERAL"
    access_level: str = "AGENCY_INTERNAL"
    property_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    contract_id: Optional[UUID] = None
    file_key: Optional[str] = None
    mime_type: str = "application/pdf"
    file_size_bytes: int = 1024


def _ser_doc(d) -> dict:
    return {
        "id": str(d.id),
        "title": d.title,
        "category": d.category,
        "access_level": d.access_level,
        "property_id": str(d.property_id) if d.property_id else None,
        "property_title": d.property.title if d.property else None,
        "customer_name": d.customer.full_name if d.customer else None,
        "contract_number": d.contract.contract_number if d.contract else None,
        "versions": [
            {
                "id": str(v.id),
                "version_number": v.version_number,
                "file_key": v.file_key,
                "mime_type": v.mime_type,
                "file_size_bytes": v.file_size_bytes,
            }
            for v in d.versions.order_by("-version_number")
        ],
        "created_at": d.created_at.isoformat(),
    }


@router.get("")
async def list_documents_endpoint(
    category: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(require_agency_context),
):
    def _op():
        from apps.documents.services import list_documents
        from common.pagination import paginate_queryset

        qs = list_documents(user=ctx.user, agency_id=ctx.agency_id, category=category)
        return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser_doc)

    items, meta = await run_django(_op, agency_id=ctx.agency_id)
    return ok(items, meta=meta)


@router.post("", status_code=201)
async def create_document_endpoint(
    body: DocumentCreateBody, ctx: RequestContext = Depends(require_agency_context)
):
    def _op():
        from apps.documents.services import create_document

        data = body.model_dump(exclude_none=True)
        doc = create_document(user=ctx.user, agency_id=ctx.agency_id, data=data)
        return _ser_doc(doc)

    return ok(await run_django(_op, agency_id=ctx.agency_id))


@router.post("/{document_id}/download")
async def download_document_endpoint(
    document_id: UUID,
    request: Request,
    ctx: RequestContext = Depends(require_agency_context),
):
    ip = request.client.host if request.client else None

    def _op():
        from apps.documents.services import log_document_download

        doc = log_document_download(
            user=ctx.user, agency_id=ctx.agency_id, document_id=document_id, ip_address=ip
        )
        latest = doc.versions.order_by("-version_number").first()
        return {
            "id": str(doc.id),
            "title": doc.title,
            "file_key": latest.file_key if latest else None,
            "download_logged": True,
        }

    return ok(await run_django(_op, agency_id=ctx.agency_id))
