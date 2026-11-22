from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from app.core.django_bridge import run_django
from app.core.security import extract_client_ip
from app.dependencies.auth import RequestContext, get_current_context, get_optional_context
from app.schemas.common import ok

router = APIRouter(tags=["CMS, SEO & Public Requests"])


class CategoryCreateBody(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=2, max_length=120)
    description: str = ""
    sort_order: int = 1


class ArticleCreateBody(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    slug: str = Field(min_length=2, max_length=240)
    article_type: str = "ARTICLE"
    category_id: Optional[UUID] = None
    summary: str = ""
    content_body: str = Field(min_length=10)
    cover_image_url: str = ""
    language: str = "fa"
    tone: str = "PROFESSIONAL"
    target_audience: str = ""
    keywords: list[str] = []
    ai_generated: bool = False
    ai_model: str = ""
    ai_tokens_used: int = 0
    meta_title: str = ""
    meta_description: str = ""
    canonical_url: str = ""
    tags: list[str] = []


class ArticlePatchBody(BaseModel):
    title: Optional[str] = None
    article_type: Optional[str] = None
    category_id: Optional[UUID] = None
    summary: Optional[str] = None
    content_body: Optional[str] = None
    cover_image_url: Optional[str] = None
    language: Optional[str] = None
    tone: Optional[str] = None
    target_audience: Optional[str] = None
    keywords: Optional[list[str]] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    canonical_url: Optional[str] = None
    change_note: str = "ویرایش تحریریه"


class ArticleStatusBody(BaseModel):
    status: str
    scheduled_for: Optional[datetime] = None


class RedirectCreateBody(BaseModel):
    from_path: str
    to_path: str
    status_code: int = 301


class ContactInquiryCreateBody(BaseModel):
    full_name: str = Field(min_length=2, max_length=140)
    phone_number: str = Field(min_length=6, max_length=24)
    email: str = ""
    inquiry_type: str = "GENERAL"
    subject: str = Field(min_length=3, max_length=200)
    message: str = Field(min_length=5)


class ContactInquiryPatchBody(BaseModel):
    status: str
    staff_response: str = ""


class CooperationSubmitBody(BaseModel):
    agency_name: str = Field(min_length=2, max_length=160)
    city: str = Field(min_length=2, max_length=100)
    manager_name: str = Field(min_length=2, max_length=140)
    manager_phone: str = Field(min_length=6, max_length=24)
    email: str = ""
    agents_count: int = 5
    license_number: str = ""
    notes: str = ""


class CooperationReviewBody(BaseModel):
    decision: str


def _ser_article(a, include_versions: bool = False) -> dict:
    data = {
        "id": str(a.id),
        "title": a.title,
        "slug": a.slug,
        "article_type": a.article_type,
        "category": {"id": str(a.category_id), "name": a.category.name, "slug": a.category.slug} if a.category else None,
        "author": {"display_name": a.author.display_name, "role_title": a.author.role_title} if a.author else None,
        "summary": a.summary,
        "content_body": a.content_body,
        "cover_image_url": a.cover_image_url,
        "status": a.status,
        "language": getattr(a, "language", "fa"),
        "tone": getattr(a, "tone", ""),
        "target_audience": getattr(a, "target_audience", ""),
        "keywords": getattr(a, "keywords", []) or [],
        "ai_generated": bool(getattr(a, "ai_generated", False)),
        "ai_model": getattr(a, "ai_model", ""),
        "ai_tokens_used": int(getattr(a, "ai_tokens_used", 0) or 0),
        "scheduled_for": a.scheduled_for.isoformat() if a.scheduled_for else None,
        "published_at": a.published_at.isoformat() if a.published_at else None,
        "meta_title": a.meta_title,
        "meta_description": a.meta_description,
        "canonical_url": a.canonical_url,
        "reading_time_minutes": a.reading_time_minutes,
        "view_count": a.view_count,
        "tags": [{"name": t.name, "slug": t.slug} for t in a.tags.all()],
        "created_at": a.created_at.isoformat(),
    }
    if include_versions:
        data["versions"] = [
            {
                "version_number": v.version_number,
                "title": v.title,
                "content_body": v.content_body,
                "change_note": v.change_note,
                "edited_by": v.edited_by.full_name if v.edited_by else "سیستم",
                "created_at": v.created_at.isoformat(),
            }
            for v in a.versions.all()[:10]
        ]
    return data


@router.get("/cms/public/categories")
async def get_public_categories():
    def _op():
        from apps.cms.services import list_categories

        return [
            {"id": str(c.id), "name": c.name, "slug": c.slug, "description": c.description}
            for c in list_categories()
        ]

    return ok(await run_django(_op))


@router.get("/cms/public/articles")
async def get_public_articles_endpoint(
    category: Optional[str] = None,
    article_type: Optional[str] = None,
    q: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    def _op():
        from apps.cms.services import list_public_articles
        from common.pagination import paginate_queryset

        qs = list_public_articles(category_slug=category, article_type=article_type, q=q)
        return paginate_queryset(qs, page=page, page_size=page_size, serializer_fn=_ser_article)

    items, meta = await run_django(_op)
    return ok(items, meta=meta)


@router.get("/cms/public/articles/{slug}")
async def get_public_article_detail(slug: str):
    def _op():
        from apps.cms.services import get_public_article

        return _ser_article(get_public_article(slug=slug))

    return ok(await run_django(_op))


@router.get("/cms/public/faqs")
async def get_public_faqs_endpoint():
    def _op():
        from apps.cms.services import list_public_faqs

        return [
            {"id": str(f.id), "category": f.category, "question": f.question, "answer": f.answer}
            for f in list_public_faqs()
        ]

    return ok(await run_django(_op))


@router.get("/cms/public/jobs")
async def get_public_jobs_endpoint():
    def _op():
        from apps.cms.services import list_public_jobs

        return [
            {
                "id": str(j.id),
                "title": j.title,
                "department": j.department,
                "location": j.location,
                "employment_type": j.employment_type,
                "description": j.description,
            }
            for j in list_public_jobs()
        ]

    return ok(await run_django(_op))


@router.get("/cms/articles")
async def list_cms_articles_endpoint(
    status: Optional[str] = None,
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.cms.services import list_cms_articles

        return [_ser_article(a, include_versions=True) for a in list_cms_articles(user=ctx.user, status_filter=status)]

    return ok(await run_django(_op))


@router.post("/cms/categories", status_code=201)
async def create_cms_category_endpoint(body: CategoryCreateBody, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.cms.services import create_category

        c = create_category(user=ctx.user, **body.model_dump())
        return {"id": str(c.id), "name": c.name, "slug": c.slug}

    return ok(await run_django(_op))


@router.post("/cms/articles", status_code=201)
async def create_cms_article_endpoint(body: ArticleCreateBody, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.cms.services import create_article

        return _ser_article(create_article(user=ctx.user, data=body.model_dump()), include_versions=True)

    return ok(await run_django(_op))


@router.patch("/cms/articles/{article_id}")
async def patch_cms_article_endpoint(
    article_id: UUID, body: ArticlePatchBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.cms.services import update_article

        return _ser_article(
            update_article(user=ctx.user, article_id=article_id, data=body.model_dump(exclude_none=True)),
            include_versions=True,
        )

    return ok(await run_django(_op))


@router.post("/cms/articles/{article_id}/status")
async def transition_cms_article_endpoint(
    article_id: UUID, body: ArticleStatusBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.cms.services import transition_article_status

        return _ser_article(
            transition_article_status(
                user=ctx.user, article_id=article_id, to_status=body.status, scheduled_for=body.scheduled_for
            ),
            include_versions=True,
        )

    return ok(await run_django(_op))


@router.delete("/cms/articles/{article_id}")
async def delete_cms_article_endpoint(
    article_id: UUID, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.cms.services import delete_article

        return delete_article(user=ctx.user, article_id=article_id)

    return ok(await run_django(_op))


@router.get("/seo/redirects")
async def list_seo_redirects_endpoint():
    def _op():
        from apps.cms.services import list_redirects

        return [
            {
                "id": str(r.id),
                "from_path": r.from_path,
                "to_path": r.to_path,
                "status_code": r.status_code,
                "is_active": r.is_active,
            }
            for r in list_redirects()
        ]

    return ok(await run_django(_op))


@router.post("/seo/redirects", status_code=201)
async def create_seo_redirect_endpoint(body: RedirectCreateBody, ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.cms.services import create_redirect

        r = create_redirect(user=ctx.user, **body.model_dump())
        return {"id": str(r.id), "from_path": r.from_path, "to_path": r.to_path, "status_code": r.status_code}

    return ok(await run_django(_op))


@router.post("/public-requests/contact", status_code=201)
async def submit_contact_inquiry_endpoint(body: ContactInquiryCreateBody):
    def _op():
        from apps.cms.services import submit_contact_inquiry

        inq = submit_contact_inquiry(data=body.model_dump())
        return {
            "id": str(inq.id),
            "tracking_code": inq.tracking_code,
            "status": inq.status,
            "created_at": inq.created_at.isoformat(),
        }

    return ok(await run_django(_op))


@router.get("/public-requests/track")
async def track_contact_inquiry_endpoint(tracking_code: str, phone_number: str):
    def _op():
        from apps.cms.services import track_contact_inquiry

        inq = track_contact_inquiry(tracking_code=tracking_code, phone_number=phone_number)
        return {
            "tracking_code": inq.tracking_code,
            "subject": inq.subject,
            "inquiry_type": inq.inquiry_type,
            "status": inq.status,
            "staff_response": inq.staff_response,
            "created_at": inq.created_at.isoformat(),
        }

    return ok(await run_django(_op))


@router.get("/cms/contact-inquiries")
async def list_contact_inquiries_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.cms.services import list_contact_inquiries

        return [
            {
                "id": str(i.id),
                "tracking_code": i.tracking_code,
                "full_name": i.full_name,
                "phone_number": i.phone_number,
                "inquiry_type": i.inquiry_type,
                "subject": i.subject,
                "message": i.message,
                "status": i.status,
                "staff_response": i.staff_response,
                "created_at": i.created_at.isoformat(),
            }
            for i in list_contact_inquiries(user=ctx.user)
        ]

    return ok(await run_django(_op))


@router.patch("/cms/contact-inquiries/{inquiry_id}")
async def patch_contact_inquiry_endpoint(
    inquiry_id: UUID, body: ContactInquiryPatchBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.cms.services import update_contact_inquiry

        i = update_contact_inquiry(
            user=ctx.user, inquiry_id=inquiry_id, status_value=body.status, staff_response=body.staff_response
        )
        return {"id": str(i.id), "status": i.status, "staff_response": i.staff_response}

    return ok(await run_django(_op))


@router.post("/public-requests/cooperation", status_code=201)
async def submit_cooperation_request_endpoint(body: CooperationSubmitBody):
    def _op():
        from apps.cms.services import submit_cooperation_request

        req = submit_cooperation_request(data=body.model_dump())
        return {
            "id": str(req.id),
            "tracking_code": req.tracking_code,
            "status": req.status,
        }

    return ok(await run_django(_op))


@router.get("/cms/cooperation-requests")
async def list_cooperation_requests_endpoint(ctx: RequestContext = Depends(get_current_context)):
    def _op():
        from apps.cms.services import list_cooperation_requests

        return [
            {
                "id": str(r.id),
                "tracking_code": r.tracking_code,
                "agency_name": r.agency_name,
                "city": r.city,
                "manager_name": r.manager_name,
                "manager_phone": r.manager_phone,
                "agents_count": r.agents_count,
                "license_number": r.license_number,
                "status": r.status,
                "approved_agency_id": str(r.approved_agency_id) if r.approved_agency_id else None,
                "created_at": r.created_at.isoformat(),
            }
            for r in list_cooperation_requests(user=ctx.user)
        ]

    return ok(await run_django(_op))


@router.post("/cms/cooperation-requests/{request_id}/review")
async def review_cooperation_request_endpoint(
    request_id: UUID, body: CooperationReviewBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.cms.services import review_cooperation_request

        r = review_cooperation_request(user=ctx.user, request_id=request_id, decision=body.decision)
        return {
            "id": str(r.id),
            "status": r.status,
            "approved_agency_id": str(r.approved_agency_id) if r.approved_agency_id else None,
        }

    return ok(await run_django(_op))


# ==============================================================================
# Legal, Rules, Privacy & Terms of Use CMS Endpoints
# ==============================================================================


class LegalSectionBody(BaseModel):
    id: Optional[str] = None
    title: str
    body_html: str = ""
    sort_order: int = 1


class LegalDocumentUpsertBody(BaseModel):
    slug: str = Field(min_length=2, max_length=120)
    doc_type: str = "LEGAL"
    title_fa: str = Field(min_length=2, max_length=240)
    title_en: str = ""
    summary: str = ""
    body_html: str = ""
    sections_json: Optional[list[LegalSectionBody]] = None
    status: str = "DRAFT"
    requires_acceptance: bool = False
    effective_at: Optional[datetime] = None
    meta_title: str = ""
    meta_description: str = ""
    sort_order: int = 100
    is_system_doc: bool = False
    change_note: str = ""


class LegalStatusBody(BaseModel):
    status: str


def _ser_legal_doc(doc, include_versions: bool = False, accepted_by_user: Optional[bool] = None) -> dict:
    payload = {
        "id": str(doc.id),
        "slug": doc.slug,
        "doc_type": doc.doc_type,
        "title_fa": doc.title_fa,
        "title_en": doc.title_en,
        "summary": doc.summary,
        "body_html": doc.body_html,
        "sections_json": doc.sections_json or [],
        "status": doc.status,
        "version_number": doc.version_number,
        "requires_acceptance": doc.requires_acceptance,
        "effective_at": doc.effective_at.isoformat() if doc.effective_at else None,
        "published_at": doc.published_at.isoformat() if doc.published_at else None,
        "meta_title": doc.meta_title,
        "meta_description": doc.meta_description,
        "sort_order": doc.sort_order,
        "is_system_doc": doc.is_system_doc,
        "updated_at": doc.updated_at.isoformat(),
    }
    if accepted_by_user is not None:
        payload["accepted_by_current_user"] = accepted_by_user
    if include_versions:
        payload["versions"] = [
            {
                "id": str(v.id),
                "version_number": v.version_number,
                "title_fa": v.title_fa,
                "summary": v.summary,
                "sections_json": v.sections_json or [],
                "change_note": v.change_note,
                "edited_by_name": v.edited_by.full_name if v.edited_by else "سیستم",
                "created_at": v.created_at.isoformat(),
            }
            for v in doc.versions.all()[:20]
        ]
    return payload


@router.get("/legal")
async def list_public_legal_endpoint(doc_type: Optional[str] = Query(default=None)):
    def _op():
        from apps.cms.services import list_legal_documents

        return [
            _ser_legal_doc(d)
            for d in list_legal_documents(doc_type=doc_type, published_only=True)
        ]

    return ok(await run_django(_op))


@router.get("/legal/{slug}")
async def get_public_legal_detail_endpoint(
    slug: str, ctx: RequestContext = Depends(get_optional_context)
):
    def _op():
        from apps.cms.services import get_public_legal_document

        doc, accepted = get_public_legal_document(slug=slug, user=ctx.user)
        return _ser_legal_doc(doc, accepted_by_user=accepted)

    return ok(await run_django(_op))


@router.post("/legal/{slug}/accept")
async def accept_legal_document_endpoint(
    slug: str, request: Request, ctx: RequestContext = Depends(get_current_context)
):
    ip = extract_client_ip(request.client.host if request.client else None)
    ua = request.headers.get("user-agent", "")

    def _op():
        from apps.cms.services import accept_legal_document

        rec = accept_legal_document(user=ctx.user, slug=slug, ip_address=ip, user_agent=ua)
        return {
            "id": str(rec.id),
            "slug": slug,
            "version_number": rec.version_number,
            "accepted_at": rec.accepted_at.isoformat(),
        }

    return ok(await run_django(_op))


@router.get("/cms/legal")
async def list_admin_legal_endpoint(
    doc_type: Optional[str] = Query(default=None),
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.cms.services import list_legal_documents

        return [
            _ser_legal_doc(d, include_versions=True)
            for d in list_legal_documents(user=ctx.user, doc_type=doc_type, published_only=False)
        ]

    return ok(await run_django(_op))


@router.post("/cms/legal", status_code=201)
async def upsert_admin_legal_endpoint(
    body: LegalDocumentUpsertBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.cms.services import upsert_legal_document

        doc = upsert_legal_document(user=ctx.user, slug=body.slug, data=body.model_dump())
        return _ser_legal_doc(doc, include_versions=True)

    return ok(await run_django(_op))


@router.get("/cms/legal/acceptances")
async def list_legal_acceptances_endpoint(
    doc_id: Optional[UUID] = Query(default=None),
    ctx: RequestContext = Depends(get_current_context),
):
    def _op():
        from apps.cms.services import list_legal_acceptances

        return [
            {
                "id": str(r.id),
                "document_slug": r.document.slug,
                "document_title": r.document.title_fa,
                "version_number": r.version_number,
                "user_name": r.user.full_name,
                "user_phone": r.user.phone_number,
                "ip_address": r.ip_address,
                "accepted_at": r.accepted_at.isoformat(),
            }
            for r in list_legal_acceptances(user=ctx.user, doc_id=doc_id)
        ]

    return ok(await run_django(_op))


@router.get("/cms/legal/{doc_id}")
async def get_admin_legal_detail_endpoint(
    doc_id: UUID, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.cms.services import get_legal_document_admin

        return _ser_legal_doc(get_legal_document_admin(user=ctx.user, doc_id=doc_id), include_versions=True)

    return ok(await run_django(_op))


@router.post("/cms/legal/{doc_id}/status")
async def transition_legal_status_endpoint(
    doc_id: UUID, body: LegalStatusBody, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.cms.services import transition_legal_status

        doc = transition_legal_status(user=ctx.user, doc_id=doc_id, to_status=body.status)
        return _ser_legal_doc(doc, include_versions=True)

    return ok(await run_django(_op))


@router.post("/cms/legal/{doc_id}/restore/{version_number}")
async def restore_legal_version_endpoint(
    doc_id: UUID, version_number: int, ctx: RequestContext = Depends(get_current_context)
):
    def _op():
        from apps.cms.services import restore_legal_version

        doc = restore_legal_version(user=ctx.user, doc_id=doc_id, version_number=version_number)
        return _ser_legal_doc(doc, include_versions=True)

    return ok(await run_django(_op))
