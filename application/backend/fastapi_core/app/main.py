from contextlib import asynccontextmanager
from django.core.exceptions import ValidationError as DjangoValidationError
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.django_bridge import init_django
from app.middleware import RequestContextMiddleware

init_django()

from common.exceptions import DomainError
from app.api.v1.auth import router as auth_router
from app.api.v1.admin import router as admin_router
from app.api.v1.agencies import router as agencies_router
from app.api.v1.team import router as team_router
from app.api.v1.properties import router as properties_router
from app.api.v1.customers import router as customers_router
from app.api.v1.crm import router as crm_router
from app.api.v1.appointments import router as appointments_router
from app.api.v1.negotiations import router as negotiations_router
from app.api.v1.contracts_deals import router as contracts_deals_router
from app.api.v1.commissions import router as commissions_router
from app.api.v1.accounting import router as accounting_router
from app.api.v1.payroll import router as payroll_router
from app.api.v1.subscriptions import router as subscriptions_router
from app.api.v1.documents import router as documents_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.reports_audit import router as reports_audit_router
from app.api.v1.settings import router as settings_router
from app.api.v1.search import router as search_router
from app.api.v1.matching import router as matching_router
from app.api.v1.support import router as support_router
from app.api.v1.complaints import router as complaints_router
from app.api.v1.surveys import router as surveys_router
from app.api.v1.push import router as push_router
from app.api.v1.ai import router as ai_router
from app.api.v1.cms import router as cms_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_django()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(_request: Request, exc: DomainError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "meta": {},
            "errors": exc.extra or {"code": exc.code, "detail": exc.message},
            "detail": exc.message,
        },
    )


@app.exception_handler(DjangoValidationError)
async def django_validation_handler(_request: Request, exc: DjangoValidationError):
    detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
    msg = detail[0] if isinstance(detail, list) and detail else str(detail)
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "data": None,
            "meta": {},
            "errors": detail,
            "detail": msg,
        },
    )


v1_router = APIRouter(prefix=settings.API_PREFIX)
v1_router.include_router(auth_router)
v1_router.include_router(admin_router)
v1_router.include_router(agencies_router)
v1_router.include_router(team_router)
v1_router.include_router(properties_router)
v1_router.include_router(customers_router)
v1_router.include_router(crm_router)
v1_router.include_router(appointments_router)
v1_router.include_router(negotiations_router)
v1_router.include_router(contracts_deals_router)
v1_router.include_router(commissions_router)
v1_router.include_router(accounting_router)
v1_router.include_router(payroll_router)
v1_router.include_router(subscriptions_router)
v1_router.include_router(documents_router)
v1_router.include_router(notifications_router)
v1_router.include_router(reports_audit_router)
v1_router.include_router(settings_router)
v1_router.include_router(search_router)
v1_router.include_router(matching_router)
v1_router.include_router(support_router)
v1_router.include_router(complaints_router)
v1_router.include_router(surveys_router)
v1_router.include_router(push_router)
v1_router.include_router(ai_router)
v1_router.include_router(cms_router)


@v1_router.get("/health")
async def health():
    return {
        "success": True,
        "data": {"service": "fastapi-django-orm", "status": "healthy"},
        "meta": {},
        "errors": None,
    }


app.include_router(v1_router)
