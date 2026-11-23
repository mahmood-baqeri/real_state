from typing import Optional
from uuid import UUID
from django.db import connection
from .context import set_current_agency_id


class TenantContextMiddleware:
    """
    Pure Django tenant context middleware for Django Admin / Celery / internal hooks.
    Resets tenant context cleanly after each invocation.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        agency_id: Optional[UUID] = None
        header_agency = request.META.get("HTTP_X_AGENCY_ID")
        if header_agency and getattr(request, "user", None) and request.user.is_authenticated:
            try:
                candidate = UUID(header_agency)
                if request.user.is_superuser or request.user.memberships.filter(
                    agency_id=candidate, status="ACTIVE"
                ).exists():
                    agency_id = candidate
            except ValueError:
                pass

        request.tenant_agency_id = agency_id
        set_current_agency_id(agency_id)

        if agency_id and connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL app.current_agency_id = %s", [str(agency_id)])

        try:
            response = self.get_response(request)
        finally:
            set_current_agency_id(None)
        return response
