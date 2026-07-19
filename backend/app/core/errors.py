from typing import Any


class AppException(Exception):
    """Base for all application exceptions. Never leaks internals to the client."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        field_errors: dict[str, list[str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.code
        self.details = details
        self.field_errors = field_errors


class ValidationError(AppException):
    status_code = 422
    code = "VALIDATION_ERROR"


class AuthenticationError(AppException):
    status_code = 401
    code = "AUTHENTICATION_ERROR"


class AuthorizationError(AppException):
    status_code = 403
    code = "AUTHORIZATION_ERROR"


class NotFoundError(AppException):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(AppException):
    """State machine violations, e.g. editing an issued invoice."""

    status_code = 409
    code = "CONFLICT"


class BusinessRuleError(AppException):
    """Domain invariant violations, e.g. credit limit exceeded."""

    status_code = 422
    code = "BUSINESS_RULE_ERROR"


class RateLimitError(AppException):
    status_code = 429
    code = "RATE_LIMITED"


class ExternalServiceError(AppException):
    """Upstream failure: S3, OCR provider, email, etc."""

    status_code = 502
    code = "EXTERNAL_SERVICE_ERROR"


class InternalError(AppException):
    status_code = 500
    code = "INTERNAL_ERROR"
