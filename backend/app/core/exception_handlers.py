from datetime import UTC, datetime

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.common.schemas import ErrorDetail, ErrorResponse
from app.core.errors import AppException, AuthenticationError, AuthorizationError

logger = structlog.get_logger("app.errors")


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _error_response(status_code: int, detail: ErrorDetail) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=detail).model_dump(mode="json"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        detail = ErrorDetail(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            field_errors=exc.field_errors,
            request_id=_request_id(request),
            timestamp=datetime.now(UTC),
        )
        if exc.status_code >= 500:
            logger.error("app_exception", code=exc.code, message=exc.message, exc_info=exc)
        return _error_response(exc.status_code, detail)

    # More specific than app_exception_handler above - Starlette dispatches to
    # the closest matching handler in the exception's MRO, so every
    # AuthenticationError/AuthorizationError subclass (InvalidCredentialsError,
    # AccountLockedError, etc. - defined in the auth module, not imported here
    # to keep core/ free of module-specific knowledge) lands here instead.
    @app.exception_handler(AuthenticationError)
    async def unauthorized_exception_handler(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        detail = ErrorDetail(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            field_errors=exc.field_errors,
            request_id=_request_id(request),
            timestamp=datetime.now(UTC),
        )
        # "Account Locked Handler": distinguished by code, not by importing
        # the auth module's AccountLockedError class into core/.
        if exc.code == "ACCOUNT_LOCKED":
            logger.warning("account_locked", request_id=_request_id(request))
        else:
            logger.info("authentication_failed", code=exc.code, request_id=_request_id(request))

        response = _error_response(exc.status_code, detail)
        response.headers["WWW-Authenticate"] = f'Bearer error="{exc.code.lower()}"'
        return response

    @app.exception_handler(AuthorizationError)
    async def forbidden_exception_handler(
        request: Request, exc: AuthorizationError
    ) -> JSONResponse:
        detail = ErrorDetail(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            field_errors=exc.field_errors,
            request_id=_request_id(request),
            timestamp=datetime.now(UTC),
        )
        logger.warning("authorization_denied", message=exc.message, request_id=_request_id(request))
        return _error_response(exc.status_code, detail)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        field_errors: dict[str, list[str]] = {}
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"] if part != "body")
            field_errors.setdefault(field, []).append(error["msg"])

        detail = ErrorDetail(
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            field_errors=field_errors,
            request_id=_request_id(request),
            timestamp=datetime.now(UTC),
        )
        return _error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, detail)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = ErrorDetail(
            code="HTTP_ERROR",
            message=str(exc.detail),
            request_id=_request_id(request),
            timestamp=datetime.now(UTC),
        )
        return _error_response(exc.status_code, detail)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", exc_info=exc)
        detail = ErrorDetail(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred. Please contact support with the request id.",
            request_id=_request_id(request),
            timestamp=datetime.now(UTC),
        )
        return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, detail)
