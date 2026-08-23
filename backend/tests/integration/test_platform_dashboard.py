"""Sprint 17 Session 5 - GET /platform/dashboard.

Mirrors tests/integration/test_platform_admin.py's helper style (Session 1).
Central claims under test: only a platform admin (never a tenant superuser)
can reach this endpoint, its counts reflect real tenant lifecycle status
mixes, its "recent tenants" section is newest-first, it exposes nothing
beyond TenantResponse's own fields, and it does not disturb the existing
GET /platform/tenants / PATCH .../status endpoints.
"""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import engine, get_db
from app.main import app
from app.modules.auth.constants import DEFAULT_TENANT_SLUG, AccountStatus, TenantStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password

_PASSWORD = "Whatever@123"
_TENANT_SUMMARY_FIELDS = {
    "id",
    "name",
    "slug",
    "status",
    "plan",
    "base_currency",
    "fiscal_year_start_month",
    "created_at",
    "updated_at",
}


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    async with engine.connect() as connection:
        await connection.begin()
        session_factory = async_sessionmaker(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        async with session_factory() as session:
            yield session
        await connection.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _default_tenant(db_session: AsyncSession) -> Tenant:
    """Explicitly the seeded default tenant by its canonical slug (Sprint 17
    Session 6) - a plain `select(Tenant).first()` is nondeterministic once
    other legitimate tenants exist in the shared dev database."""
    return (
        (await db_session.execute(select(Tenant).where(Tenant.slug == DEFAULT_TENANT_SLUG)))
        .scalars()
        .one()
    )


async def _make_tenant(
    db_session: AsyncSession, slug: str, *, status: TenantStatus = TenantStatus.ACTIVE
) -> Tenant:
    tenant = Tenant(name=f"Dashboard Test {slug}", slug=slug, status=status)
    db_session.add(tenant)
    await db_session.commit()
    return tenant


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
        password_hash=hash_password(_PASSWORD),
        full_name="Dashboard Test User",
        status=AccountStatus.ACTIVE,
        is_superuser=is_superuser,
        is_platform_admin=is_platform_admin,
    )
    db_session.add(user)
    await db_session.commit()
    return user


def _token_for(user: User) -> str:
    return create_access_token(subject=user.id, tenant_id=user.tenant_id, roles=[], permissions=[])


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token_for(user)}"}


class TestPlatformDashboardAuthorization:
    async def test_platform_admin_can_access(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _default_tenant(db_session)
        admin = await _make_user(
            db_session, tenant, email="dash-admin-test@fisherp.local", is_platform_admin=True
        )
        response = await client.get("/api/v1/platform/dashboard", headers=_auth_headers(admin))
        assert response.status_code == 200

    async def test_tenant_administrator_cannot_access(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _default_tenant(db_session)
        normal_user = await _make_user(db_session, tenant, email="dash-normal-test@fisherp.local")
        response = await client.get(
            "/api/v1/platform/dashboard", headers=_auth_headers(normal_user)
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_tenant_superuser_cannot_access(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _default_tenant(db_session)
        superuser = await _make_user(
            db_session, tenant, email="dash-superuser-test@fisherp.local", is_superuser=True
        )
        response = await client.get("/api/v1/platform/dashboard", headers=_auth_headers(superuser))
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"

    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/platform/dashboard")
        assert response.status_code == 401


class TestPlatformDashboardSummary:
    async def test_counts_reflect_mixed_tenant_statuses(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _default_tenant(db_session)
        admin = await _make_user(
            db_session, tenant, email="dash-counts-admin-test@fisherp.local", is_platform_admin=True
        )
        headers = _auth_headers(admin)

        baseline = (await client.get("/api/v1/platform/dashboard", headers=headers)).json()

        await _make_tenant(db_session, "dash-test-active", status=TenantStatus.ACTIVE)
        await _make_tenant(db_session, "dash-test-suspended", status=TenantStatus.SUSPENDED)
        await _make_tenant(db_session, "dash-test-inactive", status=TenantStatus.INACTIVE)

        body = (await client.get("/api/v1/platform/dashboard", headers=headers)).json()

        assert body["total_tenants"] == baseline["total_tenants"] + 3
        assert body["active_tenants"] == baseline["active_tenants"] + 1
        assert body["suspended_tenants"] == baseline["suspended_tenants"] + 1
        assert body["inactive_tenants"] == baseline["inactive_tenants"] + 1
        assert body["total_tenants"] == (
            body["active_tenants"] + body["suspended_tenants"] + body["inactive_tenants"]
        )

    async def test_recent_tenants_are_newest_first(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _default_tenant(db_session)
        admin = await _make_user(
            db_session, tenant, email="dash-recent-admin-test@fisherp.local", is_platform_admin=True
        )

        oldest = await _make_tenant(db_session, "dash-recent-a")
        await _make_tenant(db_session, "dash-recent-b")
        newest = await _make_tenant(db_session, "dash-recent-c")

        response = await client.get("/api/v1/platform/dashboard", headers=_auth_headers(admin))
        assert response.status_code == 200
        recent = response.json()["recent_tenants"]
        # created_at collapses to one identical value for every row created
        # inside this test's single wrapping transaction (Postgres now()
        # is transaction-start time) - id (a time-ordered uuid7) is the
        # implementation's real tiebreaker and what this test can assert on.
        recent_ids = [t["id"] for t in recent]
        assert recent_ids.index(str(newest.id)) < recent_ids.index(str(oldest.id))

    async def test_recent_tenants_expose_no_secrets_or_unrelated_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _default_tenant(db_session)
        admin = await _make_user(
            db_session, tenant, email="dash-fields-admin-test@fisherp.local", is_platform_admin=True
        )
        await _make_tenant(db_session, "dash-fields-test")

        response = await client.get("/api/v1/platform/dashboard", headers=_auth_headers(admin))
        body = response.json()

        assert set(body.keys()) == {
            "total_tenants",
            "active_tenants",
            "suspended_tenants",
            "inactive_tenants",
            "recent_tenants",
        }
        assert len(body["recent_tenants"]) > 0
        for row in body["recent_tenants"]:
            assert set(row.keys()) == _TENANT_SUMMARY_FIELDS

    async def test_existing_tenant_lifecycle_apis_are_unaffected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _default_tenant(db_session)
        admin = await _make_user(
            db_session,
            tenant,
            email="dash-regression-admin-test@fisherp.local",
            is_platform_admin=True,
        )
        headers = _auth_headers(admin)
        created = await _make_tenant(db_session, "dash-regression-test")

        dashboard_response = await client.get("/api/v1/platform/dashboard", headers=headers)
        assert dashboard_response.status_code == 200

        list_response = await client.get("/api/v1/platform/tenants", headers=headers)
        assert list_response.status_code == 200
        assert any(row["slug"] == created.slug for row in list_response.json()["data"])

        status_response = await client.patch(
            f"/api/v1/platform/tenants/{created.id}/status",
            json={"status": "suspended"},
            headers=headers,
        )
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "suspended"
