class DomainError(Exception):
    """Base exception raised by Django domain services and translated cleanly by FastAPI."""

    code: str = "DOMAIN_ERROR"
    status_code: int = 400

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None, extra=None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.extra = extra


class ValidationDomainError(DomainError):
    code = "VALIDATION_ERROR"
    status_code = 400


class AuthenticationDomainError(DomainError):
    code = "AUTHENTICATION_FAILED"
    status_code = 401


class PermissionDeniedDomainError(DomainError):
    code = "PERMISSION_DENIED"
    status_code = 403


class NotFoundDomainError(DomainError):
    code = "NOT_FOUND"
    status_code = 404


class ConflictDomainError(DomainError):
    code = "CONFLICT"
    status_code = 409
