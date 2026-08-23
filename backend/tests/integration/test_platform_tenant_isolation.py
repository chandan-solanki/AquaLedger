"""Sprint 17 Session 2 - tenant isolation around the new platform endpoints.

Central claim: provisioning/managing tenants through /platform/tenants has
zero effect on ordinary tenant-scoped business endpoints. A platform admin
calling GET /fish still only sees their own tenant's rows, even immediately
after creating a brand-new tenant through the provisioning endpoint. Mirrors
tests/integration/test_platform_admin.py's isolation tests (Session 1) but
exercises a REAL provisioned tenant rather than a hand-inserted one.
"""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import engine, get_db
from app.main import app
from app.modules.auth.constants import DEFAULT_TENANT_SLUG, AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password
from app.modules.fish.models import Fish


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


async def _make_user(
    db_session: AsyncSession, tenant: Tenant, *, email: str, is_platform_admin: bool = False
) -> User:
    user = User(
        tenant_id=tenant.id,
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password("Whatever@123"),
        full_name="Isolation Test User",
        status=AccountStatus.ACTIVE,
        is_platform_admin=is_platform_admin,
    )
    db_session.add(user)
    await db_session.commit()
    return user


def _token_for(user: User, *, permissions: list[str] | None = None) -> str:
    return create_access_token(
        subject=user.id, tenant_id=user.tenant_id, roles=[], permissions=permissions or []
    )


class TestProvisioningDoesNotWidenBusinessQueries:
    async def test_platform_admin_provisioning_a_tenant_stays_scoped_to_their_own_tenant_fish(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session,
            default_tenant,
            email="isolation-pa@fisherp.local",
            is_platform_admin=True,
        )
        own_fish = Fish(
            tenant_id=default_tenant.id, code="ISOL-PA", name="Platform Admin's Own Tenant Fish"
        )
        db_session.add(own_fish)
        await db_session.commit()

        create_response = await client.post(
            "/api/v1/platform/tenants",
            json={
                "name": "Isolation Test Tenant",
                "slug": "isolation-test-tenant",
                "administrator": {
                    "email": "isolation-owner@newtenant.example",
                    "username": "isolationowner",
                    "full_name": "New Tenant Owner",
                    "password": "TempPass@123",
                },
            },
            headers={"Authorization": f"Bearer {_token_for(platform_admin)}"},
        )
        assert create_response.status_code == 201
        new_tenant_id = create_response.json()["tenant"]["id"]

        # The platform admin's own token still only ever sees their own
        # tenant's fish - creating another tenant did not widen this query.
        fish_response = await client.get(
            "/api/v1/fish",
            headers={
                "Authorization": f"Bearer {_token_for(platform_admin, permissions=['fish:view'])}"
            },
        )
        assert fish_response.status_code == 200
        names = {row["name"] for row in fish_response.json()["data"]}
        assert "Platform Admin's Own Tenant Fish" in names
        assert new_tenant_id not in {row["tenant_id"] for row in fish_response.json()["data"]}

    async def test_new_tenants_administrator_cannot_see_other_tenants_fish(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session, default_tenant, email="isolation-pa-2@fisherp.local", is_platform_admin=True
        )
        other_fish = Fish(
            tenant_id=default_tenant.id, code="ISOL-OTHER", name="Default Tenant Only Fish"
        )
        db_session.add(other_fish)
        await db_session.commit()

        create_response = await client.post(
            "/api/v1/platform/tenants",
            json={
                "name": "Second Isolation Tenant",
                "slug": "second-isolation-tenant",
                "administrator": {
                    "email": "second-owner@newtenant.example",
                    "username": "secondowner",
                    "full_name": "Second Tenant Owner",
                    "password": "TempPass@123",
                },
            },
            headers={"Authorization": f"Bearer {_token_for(platform_admin)}"},
        )
        assert create_response.status_code == 201

        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "second-owner@newtenant.example", "password": "TempPass@123"},
        )
        assert login_response.status_code == 200
        new_admin_token = login_response.json()["access_token"]

        fish_response = await client.get(
            "/api/v1/fish", headers={"Authorization": f"Bearer {new_admin_token}"}
        )
        assert fish_response.status_code == 200
        names = {row["name"] for row in fish_response.json()["data"]}
        assert "Default Tenant Only Fish" not in names

        # Confirms the new tenant's admin also cannot reach platform endpoints.
        platform_response = await client.get(
            "/api/v1/platform/me", headers={"Authorization": f"Bearer {new_admin_token}"}
        )
        assert platform_response.status_code == 403

    async def test_tenant_superuser_still_cannot_call_platform_tenant_endpoints(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        superuser = await _make_user(
            db_session, default_tenant, email="isolation-superuser@fisherp.local"
        )
        superuser.is_superuser = True
        await db_session.commit()

        response = await client.get(
            "/api/v1/platform/tenants",
            headers={"Authorization": f"Bearer {_token_for(superuser)}"},
        )
        assert response.status_code == 403
