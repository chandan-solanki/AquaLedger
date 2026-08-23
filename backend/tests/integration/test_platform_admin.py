"""Sprint 17 Session 1 - platform-admin authorization boundary.

Mirrors tests/integration/test_rbac.py's pattern (a private test router
exercising the dependency directly over real HTTP) plus real-endpoint and
cross-tenant regression coverage. The central claim under test: is_superuser
and is_platform_admin are two independent flags - neither one satisfies the
other's check, and is_platform_admin never widens a tenant_id filter on an
ordinary business endpoint.
"""

from collections.abc import AsyncGenerator

import pytest
from fastapi import Depends, FastAPI
from fastapi.routing import APIRouter
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exception_handlers import register_exception_handlers
from app.db.session import get_db
from app.modules.auth.constants import DEFAULT_TENANT_SLUG, AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.permissions import require_platform_admin
from app.modules.auth.security import create_access_token, hash_password
from app.modules.fish.models import Fish

# Never included in app.main - exercises require_platform_admin in isolation,
# the same way test_rbac.py's _test_router exercises require_permission/require_role.
_test_router = APIRouter()


@_test_router.get("/needs-platform-admin")
async def _needs_platform_admin(
    _: None = Depends(require_platform_admin),
) -> dict[str, bool]:
    return {"ok": True}


def _build_platform_test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(_test_router)
    return app


@pytest.fixture
async def platform_test_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    app = _build_platform_test_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


async def _default_tenant(db_session: AsyncSession) -> Tenant:
    """Explicitly the seeded default tenant by its canonical slug (Sprint 17
    Session 6) - a plain `select(Tenant).first()` is nondeterministic once
    other legitimate tenants exist in the shared dev database."""
    return (
        (await db_session.execute(select(Tenant).where(Tenant.slug == DEFAULT_TENANT_SLUG)))
        .scalars()
        .one()
    )


async def _make_user(
    db_session: AsyncSession,
    tenant: Tenant,
    *,
    email: str,
    is_superuser: bool = False,
    is_platform_admin: bool = False,
) -> User:
    user = User(
        tenant_id=tenant.id,
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password("Whatever@123"),
        full_name="Platform Admin Test User",
        status=AccountStatus.ACTIVE,
        is_superuser=is_superuser,
        is_platform_admin=is_platform_admin,
    )
    db_session.add(user)
    await db_session.commit()
    return user


def _token_for(
    user: User, *, roles: list[str] | None = None, permissions: list[str] | None = None
) -> str:
    return create_access_token(
        subject=user.id,
        tenant_id=user.tenant_id,
        roles=roles or [],
        permissions=permissions or [],
    )


class TestRequirePlatformAdmin:
    async def test_normal_user_is_denied(
        self, platform_test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _default_tenant(db_session)
        user = await _make_user(db_session, tenant, email="normal-platform-test@fisherp.local")
        response = await platform_test_client.get(
            "/needs-platform-admin", headers={"Authorization": f"Bearer {_token_for(user)}"}
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_tenant_superuser_is_denied_without_platform_authority(
        self, platform_test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _default_tenant(db_session)
        superuser = await _make_user(
            db_session, tenant, email="superuser-platform-test@fisherp.local", is_superuser=True
        )
        response = await platform_test_client.get(
            "/needs-platform-admin", headers={"Authorization": f"Bearer {_token_for(superuser)}"}
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_platform_admin_is_authorized(
        self, platform_test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _default_tenant(db_session)
        admin = await _make_user(
            db_session, tenant, email="platform-admin-test@fisherp.local", is_platform_admin=True
        )
        response = await platform_test_client.get(
            "/needs-platform-admin", headers={"Authorization": f"Bearer {_token_for(admin)}"}
        )
        assert response.status_code == 200

    async def test_requires_authentication(self, platform_test_client: AsyncClient) -> None:
        response = await platform_test_client.get("/needs-platform-admin")
        assert response.status_code == 401


class TestPlatformMeEndpoint:
    """Same checks against the real, registered GET /api/v1/platform/me."""

    async def test_normal_user_gets_403(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _default_tenant(db_session)
        user = await _make_user(db_session, tenant, email="me-normal-test@fisherp.local")
        response = await client.get(
            "/api/v1/platform/me", headers={"Authorization": f"Bearer {_token_for(user)}"}
        )
        assert response.status_code == 403

    async def test_tenant_superuser_gets_403(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _default_tenant(db_session)
        superuser = await _make_user(
            db_session, tenant, email="me-superuser-test@fisherp.local", is_superuser=True
        )
        response = await client.get(
            "/api/v1/platform/me", headers={"Authorization": f"Bearer {_token_for(superuser)}"}
        )
        assert response.status_code == 403

    async def test_platform_admin_gets_own_identity(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _default_tenant(db_session)
        admin = await _make_user(
            db_session, tenant, email="me-platform-admin-test@fisherp.local", is_platform_admin=True
        )
        response = await client.get(
            "/api/v1/platform/me", headers={"Authorization": f"Bearer {_token_for(admin)}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(admin.id)
        assert body["tenant_id"] == str(tenant.id)
        assert body["is_platform_admin"] is True


class TestPlatformAdminDoesNotBypassTenantIsolation:
    """The security-critical guarantee: adding is_platform_admin must not
    silently make an existing tenant-scoped business endpoint cross-tenant."""

    async def test_platform_admin_still_only_sees_their_own_tenant_fish(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_a = await _default_tenant(db_session)
        tenant_b = Tenant(name="Throwaway Tenant B", slug="throwaway-tenant-b-platform-test")
        db_session.add(tenant_b)
        await db_session.flush()

        fish_a = Fish(tenant_id=tenant_a.id, code="PLTF-A", name="Platform Test Pomfret A")
        fish_b = Fish(tenant_id=tenant_b.id, code="PLTF-B", name="Platform Test Pomfret B")
        db_session.add_all([fish_a, fish_b])
        await db_session.commit()

        platform_admin = await _make_user(
            db_session,
            tenant_a,
            email="fish-platform-admin-test@fisherp.local",
            is_platform_admin=True,
        )
        token = _token_for(platform_admin, roles=["operator"], permissions=["fish:view"])

        response = await client.get("/api/v1/fish", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        names = {row["name"] for row in response.json()["data"]}
        assert "Platform Test Pomfret A" in names
        assert "Platform Test Pomfret B" not in names

    async def test_tenant_b_normal_user_cannot_see_tenant_a_fish(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_a = await _default_tenant(db_session)
        tenant_b = Tenant(name="Throwaway Tenant B2", slug="throwaway-tenant-b2-platform-test")
        db_session.add(tenant_b)
        await db_session.flush()

        fish_a = Fish(tenant_id=tenant_a.id, code="PLTF-C", name="Isolation Test Pomfret A")
        db_session.add(fish_a)
        await db_session.commit()

        tenant_b_user = await _make_user(
            db_session, tenant_b, email="tenant-b-normal-test@fisherp.local"
        )
        token = _token_for(tenant_b_user, roles=["operator"], permissions=["fish:view"])

        response = await client.get("/api/v1/fish", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        names = {row["name"] for row in response.json()["data"]}
        assert "Isolation Test Pomfret A" not in names
