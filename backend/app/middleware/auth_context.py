from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.modules.auth.exceptions import ExpiredTokenError, InvalidTokenError
from app.modules.auth.security import decode_access_token

_BEARER_PREFIX = "bearer "


class AuthContextMiddleware(BaseHTTPMiddleware):
    """Best-effort request-scoped auth context, derived from the JWT alone.

    This does NOT enforce authentication - most routes are public (health,
    login, docs), and middleware runs before route matching so it has no way
    to know which route requires what. Enforcement stays with the
    get_current_user/require_permission/require_role dependencies. All this
    does is make user_id/tenant_id/roles/permissions available on
    request.state, and bind user_id/tenant_id into the structlog context so
    every log line for this request carries them (ARCHITECTURE §22).
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.user_id = None
        request.state.tenant_id = None
        request.state.roles = []
        request.state.permissions = []

        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith(_BEARER_PREFIX):
            token = auth_header[len(_BEARER_PREFIX) :]
            try:
                payload = decode_access_token(token)
            except (InvalidTokenError, ExpiredTokenError):
                payload = None

            if payload is not None:
                request.state.user_id = str(payload.sub)
                request.state.tenant_id = str(payload.tenant_id)
                request.state.roles = payload.roles
                request.state.permissions = payload.permissions
                structlog.contextvars.bind_contextvars(
                    user_id=request.state.user_id, tenant_id=request.state.tenant_id
                )

        return await call_next(request)
