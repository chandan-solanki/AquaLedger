from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.db.session import engine
from app.middleware.auth_context import AuthContextMiddleware
from app.middleware.logging import StructuredLoggingMiddleware
from app.middleware.request_id import RequestIDMiddleware

settings = get_settings()
configure_logging()
logger = structlog.get_logger("app")

_DESCRIPTION = """
ERP backend for the seafood trading industry.

## Authentication

Most endpoints require a JWT access token. Obtain one from
`POST /api/v1/auth/login`, then click **Authorize** above and paste the
`access_token` value (no `Bearer ` prefix needed - Swagger adds it).

- Access tokens expire quickly (see `expires_in` in the login response);
  use `POST /api/v1/auth/refresh` with the `refresh_token` to get a new pair.
- `POST /api/v1/auth/logout` revokes a single refresh token.
- A refresh token that's already been rotated (used more than once) is
  treated as stolen: the entire session family is revoked immediately.
"""

_OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": "Login, token refresh, logout, current-user profile, and password change.",
    },
    {"name": "companies", "description": "Customer/supplier company records (CRUD)."},
    {
        "name": "boats",
        "description": "Fishing boat master data, owned by a company (CRUD, search, filters).",
    },
    {"name": "trips", "description": "Fishing/transport trips performed by a boat (CRUD)."},
    {
        "name": "trip-catches",
        "description": "Fish landed on a trip - the inventory source for sales invoices (CRUD).",
    },
    {
        "name": "trip-expenses",
        "description": (
            "Operational expenses incurred during a fishing trip - CRUD, search, "
            "filtering, sorting and pagination, with trip-window and cancelled-trip "
            "business rules enforced server-side."
        ),
    },
    {"name": "health", "description": "Liveness check."},
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    logger.info("app_startup", app_env=settings.app_env)
    yield
    await engine.dispose()
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=_DESCRIPTION,
        version="0.1.0",
        openapi_tags=_OPENAPI_TAGS,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Middleware order matters: added first = closest to the router.
    # Execution order on a request is the reverse:
    # RequestID -> AuthContext -> Logging -> CORS -> router.
    # AuthContext must run after RequestID's clear_contextvars() (otherwise its
    # user_id/tenant_id binding would be wiped) and before Logging's completion
    # log line, so the log carries both.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(StructuredLoggingMiddleware)
    app.add_middleware(AuthContextMiddleware)
    app.add_middleware(RequestIDMiddleware)

    register_exception_handlers(app)

    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
