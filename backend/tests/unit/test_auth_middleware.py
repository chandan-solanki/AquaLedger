import uuid

from starlette.requests import Request
from starlette.responses import Response

from app.middleware.auth_context import AuthContextMiddleware
from app.modules.auth.security import create_access_token


def _make_request(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope)


async def _noop_app(scope: object, receive: object, send: object) -> None:
    return None


def _make_middleware() -> AuthContextMiddleware:
    return AuthContextMiddleware(app=_noop_app)


class TestAuthContextMiddleware:
    async def test_populates_state_for_valid_token(self) -> None:
        subject = uuid.uuid4()
        tenant_id = uuid.uuid4()
        token = create_access_token(
            subject=subject, tenant_id=tenant_id, roles=["admin"], permissions=["invoice:issue"]
        )
        request = _make_request({"Authorization": f"Bearer {token}"})
        captured: dict[str, object] = {}

        async def call_next(req: Request) -> Response:
            captured["user_id"] = req.state.user_id
            captured["tenant_id"] = req.state.tenant_id
            captured["roles"] = req.state.roles
            captured["permissions"] = req.state.permissions
            return Response()

        await _make_middleware().dispatch(request, call_next)

        assert captured["user_id"] == str(subject)
        assert captured["tenant_id"] == str(tenant_id)
        assert captured["roles"] == ["admin"]
        assert captured["permissions"] == ["invoice:issue"]

    async def test_leaves_state_empty_without_header(self) -> None:
        request = _make_request({})
        captured: dict[str, object] = {}

        async def call_next(req: Request) -> Response:
            captured["user_id"] = req.state.user_id
            return Response()

        await _make_middleware().dispatch(request, call_next)

        assert captured["user_id"] is None

    async def test_leaves_state_empty_for_garbage_token(self) -> None:
        request = _make_request({"Authorization": "Bearer not-a-real-jwt"})
        captured: dict[str, object] = {}

        async def call_next(req: Request) -> Response:
            captured["user_id"] = req.state.user_id
            return Response()

        await _make_middleware().dispatch(request, call_next)

        assert captured["user_id"] is None

    async def test_ignores_non_bearer_scheme(self) -> None:
        request = _make_request({"Authorization": "Basic dXNlcjpwYXNz"})
        captured: dict[str, object] = {}

        async def call_next(req: Request) -> Response:
            captured["user_id"] = req.state.user_id
            return Response()

        await _make_middleware().dispatch(request, call_next)

        assert captured["user_id"] is None
