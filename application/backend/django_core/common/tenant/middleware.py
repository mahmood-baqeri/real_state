from typing import Optional
from uuid import UUID
from django.db import connection, transaction
from .context import set_current_agency_id


class TenantContextMiddleware:
    """Bind a verified user/agency to request-local transaction RLS context."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        user_id = getattr(user, "id", None) if user and user.is_authenticated else None
        agency_id: Optional[UUID] = None
        set_current_agency_id(None)
        try:
            with transaction.atomic():
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT set_config('app.current_user_id', %s, true)",
                            [str(user_id) if user_id else ""],
                        )
                header_agency = request.META.get("HTTP_X_AGENCY_ID")
                if header_agency and user_id:
                    try:
                        candidate = UUID(header_agency)
                        if user.is_superuser or user.memberships.filter(
                            agency_id=candidate, status="ACTIVE"
                        ).exists():
                            agency_id = candidate
                    except (ValueError, TypeError):
                        agency_id = None
                request.tenant_agency_id = agency_id
                set_current_agency_id(agency_id)
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT set_config('app.current_agency_id', %s, true)",
                            [str(agency_id) if agency_id else ""],
                        )
                return self.get_response(request)
        finally:
            set_current_agency_id(None)
