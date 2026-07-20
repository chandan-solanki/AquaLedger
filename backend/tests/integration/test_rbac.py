from collections.abc import AsyncGenerator

import pytest
from fastapi import Depends, FastAPI
from fastapi.routing import APIRouter
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exception_handlers import register_exception_handlers
from app.db.session import get_db
from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.permissions import require_permission, require_role
from app.modules.auth.security import create_access_token, hash_password

# This router exists only for this test file - it is never included in the
# real app (app.main). It exercises require_permission/require_role over
# real HTTP, which a business module would use once one exists.
_test_router = APIRouter()


@_test_router.get("/needs-permission")
async def _needs_permission(
    _: None = Depends(require_permission("company:view")),
) -> dict[str, bool]:
    return {"ok": True}


@_test_router.get("/needs-missing-permission")
async def _needs_missing_permission(
    _: None = Depends(require_permission("settings:manage")),
) -> dict[str, bool]:
    return {"ok": True}


@_test_router.get("/needs-role")
async def _needs_role(_: None = Depends(require_role("operator"))) -> dict[str, bool]:
    return {"ok": True}


@_test_router.get("/needs-missing-role")
async def _needs_missing_role(_: None = Depends(require_role("accountant"))) -> dict[str, bool]:
    return {"ok": True}


def _build_rbac_test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(_test_router)
    return app


@pytest.fixture
async def rbac_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    app = _build_rbac_test_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


async def _make_operator_user(db_session: AsyncSession) -> User:
    """A real, non-superuser DB row (needed by get_current_user's lookup),
    with hand-crafted token claims - no need to wire real role/permission
    seed data to control exactly what a test scenario grants."""
    tenant = (await db_session.execute(select(Tenant))).scalars().first()
    assert tenant is not None
    user = User(
        tenant_id=tenant.id,
        email="operator-rbac-test@fisherp.local",
        username="operator-rbac-test",
        password_hash=hash_password("Whatever@123"),
        full_name="RBAC Test Operator",
        status=AccountStatus.ACTIVE,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user


class TestRequirePermission:
    async def test_allows_when_token_has_the_permission(
        self, rbac_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_operator_user(db_session)
        token = create_access_token(
            subject=user.id,
            tenant_id=user.tenant_id,
            roles=["operator"],
            permissions=["company:view", "fish:view", "invoice:view"],
        )
        response = await rbac_client.get(
            "/needs-permission", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    async def test_denies_when_token_lacks_the_permission(
        self, rbac_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_operator_user(db_session)
        token = create_access_token(
            subject=user.id,
            tenant_id=user.tenant_id,
            roles=["operator"],
            permissions=["company:view", "fish:view", "invoice:view"],
        )
        response = await rbac_client.get(
            "/needs-missing-permission", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_superuser_bypasses_permission_check(
        self, rbac_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = (await db_session.execute(select(Tenant))).scalars().first()
        assert tenant is not None
        superuser = User(
            tenant_id=tenant.id,
            email="superuser-rbac-test@fisherp.local",
            username="superuser-rbac-test",
            password_hash=hash_password("Whatever@123"),
            full_name="RBAC Test Superuser",
            status=AccountStatus.ACTIVE,
            is_superuser=True,
        )
        db_session.add(superuser)
        await db_session.commit()

        token = create_access_token(
            subject=superuser.id, tenant_id=superuser.tenant_id, roles=[], permissions=[]
        )
        response = await rbac_client.get(
            "/needs-missing-permission", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    async def test_requires_authentication(self, rbac_client: AsyncClient) -> None:
        response = await rbac_client.get("/needs-permission")
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"].startswith("Bearer")


class TestRequireRole:
    async def test_allows_when_token_has_the_role(
        self, rbac_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_operator_user(db_session)
        token = create_access_token(
            subject=user.id, tenant_id=user.tenant_id, roles=["operator"], permissions=[]
        )
        response = await rbac_client.get(
            "/needs-role", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    async def test_denies_when_token_lacks_the_role(
        self, rbac_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_operator_user(db_session)
        token = create_access_token(
            subject=user.id, tenant_id=user.tenant_id, roles=["operator"], permissions=[]
        )
        response = await rbac_client.get(
            "/needs-missing-role", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403

    async def test_locked_account_is_rejected_before_role_check(
        self, rbac_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_operator_user(db_session)
        user.status = AccountStatus.INACTIVE
        await db_session.commit()

        token = create_access_token(
            subject=user.id, tenant_id=user.tenant_id, roles=["operator"], permissions=[]
        )
        response = await rbac_client.get(
            "/needs-role", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "ACCOUNT_DISABLED"
