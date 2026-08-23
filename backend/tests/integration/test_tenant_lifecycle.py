"""Sprint 17 Session 2 - tenant lifecycle (TenantStatus) enforcement.

Central claims under test: a non-ACTIVE tenant blocks login, refresh, and
use of an already-issued access token, uniformly - including its own
tenant superusers and any platform admin who happens to belong to it (no
exemption). The lifecycle-mutation endpoint itself carries a narrow
guardrail against ever leaving zero platform admins reachable anywhere.
"""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import engine, get_db
from app.main import app
from app.modules.auth.constants import DEFAULT_TENANT_SLUG, AccountStatus, TenantStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password

_PASSWORD = "Whatever@123"


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


async def _suspend_other_reachable_platform_admin_tenants(
    db_session: AsyncSession, *, excluding_tenant_id
) -> None:
    """Sprint 17 Session 6: deterministically constructs a true "lone
    reachable platform admin" scenario within this test's own rolled-back
    transaction. The persistent dev platform-admin@fisherp.local (and any
    other real platform admin created by manual testing) would otherwise
    make the tenant under test NOT actually the only one with a reachable
    platform admin - mirrors
    TenantRepository.count_platform_admins_in_active_tenants' own predicate
    exactly. Only ever flips a Tenant's `status` column - never a User row,
    and never platform-admin@fisherp.local's account itself - and nothing
    here survives the test's guaranteed rollback.
    """
    other_tenant_ids = (
        (
            await db_session.execute(
                select(Tenant.id)
                .join(User, User.tenant_id == Tenant.id)
                .where(
                    User.is_platform_admin.is_(True),
                    User.deleted_at.is_(None),
                    User.status == AccountStatus.ACTIVE,
                    Tenant.status == TenantStatus.ACTIVE,
                    Tenant.id != excluding_tenant_id,
                )
                .distinct()
            )
        )
        .scalars()
        .all()
    )
    if other_tenant_ids:
        await db_session.execute(
            update(Tenant)
            .where(Tenant.id.in_(other_tenant_ids))
            .values(status=TenantStatus.SUSPENDED)
        )


async def _make_tenant(db_session: AsyncSession, slug: str) -> Tenant:
    tenant = Tenant(name=f"Lifecycle Test {slug}", slug=slug, status=TenantStatus.ACTIVE)
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
        full_name="Lifecycle Test User",
        status=AccountStatus.ACTIVE,
        is_superuser=is_superuser,
        is_platform_admin=is_platform_admin,
    )
    db_session.add(user)
    await db_session.commit()
    return user


def _token_for(user: User) -> str:
    return create_access_token(subject=user.id, tenant_id=user.tenant_id, roles=[], permissions=[])


async def _login(client: AsyncClient, email: str) -> Response:
    return await client.post("/api/v1/auth/login", json={"email": email, "password": _PASSWORD})


async def _suspend(
    client: AsyncClient, platform_admin: User, tenant_id, new_status: str = "suspended"
) -> None:
    response = await client.patch(
        f"/api/v1/platform/tenants/{tenant_id}/status",
        json={"status": new_status},
        headers={"Authorization": f"Bearer {_token_for(platform_admin)}"},
    )
    assert response.status_code == 200, response.text


class TestActiveTenantBaseline:
    async def test_active_tenant_user_can_log_in(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _make_tenant(db_session, "lifecycle-active")
        await _make_user(db_session, tenant, email="active-user@lifecycle.example")
        response = await _login(client, "active-user@lifecycle.example")
        assert response.status_code == 200


class TestSuspendedTenant:
    async def test_new_login_denied(self, client: AsyncClient, db_session: AsyncSession) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session, default_tenant, email="suspend-pa-1@fisherp.local", is_platform_admin=True
        )
        target = await _make_tenant(db_session, "lifecycle-suspend-login")
        await _make_user(db_session, target, email="blocked-login@lifecycle.example")
        await _suspend(client, platform_admin, target.id)

        response = await _login(client, "blocked-login@lifecycle.example")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "TENANT_SUSPENDED"

    async def test_existing_access_token_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session, default_tenant, email="suspend-pa-2@fisherp.local", is_platform_admin=True
        )
        target = await _make_tenant(db_session, "lifecycle-suspend-token")
        user = await _make_user(db_session, target, email="blocked-token@lifecycle.example")
        token = _token_for(user)  # issued while the tenant is still active

        await _suspend(client, platform_admin, target.id)

        response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "TENANT_SUSPENDED"

    async def test_refresh_token_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session, default_tenant, email="suspend-pa-3@fisherp.local", is_platform_admin=True
        )
        target = await _make_tenant(db_session, "lifecycle-suspend-refresh")
        await _make_user(db_session, target, email="blocked-refresh@lifecycle.example")

        login_response = await _login(client, "blocked-refresh@lifecycle.example")
        refresh_token = login_response.json()["refresh_token"]

        await _suspend(client, platform_admin, target.id)

        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert response.status_code == 401
        # INVALID_TOKEN, not TENANT_SUSPENDED: suspending a tenant proactively
        # revokes every refresh token belonging to its users (defense in
        # depth, AuthRepository.revoke_all_for_tenant), so refresh's own
        # reuse-detection rejects the now-revoked token before
        # raise_if_tenant_blocked would even run - a stronger guarantee
        # (the token is provably dead), just via a different, equally-401
        # error code.
        assert response.json()["error"]["code"] == "INVALID_TOKEN"

    async def test_tenant_superuser_is_also_blocked(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session, default_tenant, email="suspend-pa-4@fisherp.local", is_platform_admin=True
        )
        target = await _make_tenant(db_session, "lifecycle-suspend-superuser")
        await _make_user(
            db_session, target, email="blocked-superuser@lifecycle.example", is_superuser=True
        )
        await _suspend(client, platform_admin, target.id)

        response = await _login(client, "blocked-superuser@lifecycle.example")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "TENANT_SUSPENDED"

    async def test_platform_admin_belonging_to_the_suspended_tenant_is_also_blocked(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """No exemption: a platform admin whose OWN tenant is suspended
        cannot authenticate at all - not even to reach /platform/me. This
        is the deliberate default the session's audit chose; the lockout
        risk this creates is mitigated by the guardrail on the status-change
        mutation itself (TestLastReachablePlatformAdminGuardrail below), not
        by exempting platform admins here."""
        default_tenant = await _default_tenant(db_session)
        acting_platform_admin = await _make_user(
            db_session,
            default_tenant,
            email="suspend-pa-5-actor@fisherp.local",
            is_platform_admin=True,
        )
        target = await _make_tenant(db_session, "lifecycle-suspend-pa-self")
        victim_platform_admin = await _make_user(
            db_session,
            target,
            email="suspend-pa-5-victim@lifecycle.example",
            is_platform_admin=True,
        )
        await _suspend(client, acting_platform_admin, target.id)

        response = await _login(client, "suspend-pa-5-victim@lifecycle.example")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "TENANT_SUSPENDED"

        # Even a still-valid access token for that platform admin is rejected.
        token = _token_for(victim_platform_admin)
        me_response = await client.get(
            "/api/v1/platform/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == 401
        assert me_response.json()["error"]["code"] == "TENANT_SUSPENDED"


class TestInactiveTenant:
    async def test_inactive_tenant_login_denied_with_distinct_code(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session, default_tenant, email="inactive-pa-1@fisherp.local", is_platform_admin=True
        )
        target = await _make_tenant(db_session, "lifecycle-inactive")
        await _make_user(db_session, target, email="blocked-inactive@lifecycle.example")
        await _suspend(client, platform_admin, target.id, new_status="inactive")

        response = await _login(client, "blocked-inactive@lifecycle.example")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "TENANT_INACTIVE"


class TestReactivation:
    async def test_reactivated_tenant_can_authenticate_again(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session,
            default_tenant,
            email="reactivate-pa-1@fisherp.local",
            is_platform_admin=True,
        )
        target = await _make_tenant(db_session, "lifecycle-reactivate")
        await _make_user(db_session, target, email="reactivate-user@lifecycle.example")

        await _suspend(client, platform_admin, target.id)
        blocked = await _login(client, "reactivate-user@lifecycle.example")
        assert blocked.status_code == 401

        await _suspend(client, platform_admin, target.id, new_status="active")
        restored = await _login(client, "reactivate-user@lifecycle.example")
        assert restored.status_code == 200


class TestStatusChangeGuardsAndAudit:
    async def test_unchanged_status_is_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session, default_tenant, email="unchanged-pa@fisherp.local", is_platform_admin=True
        )
        target = await _make_tenant(db_session, "lifecycle-unchanged")
        response = await client.patch(
            f"/api/v1/platform/tenants/{target.id}/status",
            json={"status": "active"},
            headers={"Authorization": f"Bearer {_token_for(platform_admin)}"},
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "TENANT_STATUS_UNCHANGED"

    async def test_status_change_creates_audit_record_against_actors_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.modules.auth.models import AuditLog

        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session, default_tenant, email="audit-pa@fisherp.local", is_platform_admin=True
        )
        target = await _make_tenant(db_session, "lifecycle-audit")
        await _suspend(client, platform_admin, target.id)

        audit_row = (
            await db_session.execute(
                select(AuditLog).where(
                    AuditLog.action == "tenant_status_changed", AuditLog.entity_id == target.id
                )
            )
        ).scalar_one()
        assert audit_row.tenant_id == platform_admin.tenant_id
        assert audit_row.user_id == platform_admin.id
        assert audit_row.changes == {"status": {"old": "active", "new": "suspended"}}


class TestLastReachablePlatformAdminGuardrail:
    async def test_suspending_the_only_reachable_platform_admins_tenant_is_blocked(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        lone_tenant = await _make_tenant(db_session, "lifecycle-lone-platform-admin")
        lone_admin = await _make_user(
            db_session, lone_tenant, email="lone-pa@lifecycle.example", is_platform_admin=True
        )
        # Explicitly constructed, not assumed: any other real platform admin
        # (e.g. the persistent dev platform-admin@fisherp.local) is
        # temporarily suspended-by-tenant for this test only, so lone_admin
        # is deterministically the sole reachable platform admin.
        await _suspend_other_reachable_platform_admin_tenants(
            db_session, excluding_tenant_id=lone_tenant.id
        )
        response = await client.patch(
            f"/api/v1/platform/tenants/{lone_tenant.id}/status",
            json={"status": "suspended"},
            headers={"Authorization": f"Bearer {_token_for(lone_admin)}"},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "LAST_REACHABLE_PLATFORM_ADMIN"

        unchanged = (
            await db_session.execute(select(Tenant).where(Tenant.id == lone_tenant.id))
        ).scalar_one()
        assert unchanged.status == TenantStatus.ACTIVE

    async def test_suspension_allowed_when_another_platform_admin_remains_reachable(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_c = await _make_tenant(db_session, "lifecycle-guardrail-c")
        tenant_d = await _make_tenant(db_session, "lifecycle-guardrail-d")
        admin_c = await _make_user(
            db_session, tenant_c, email="guardrail-c@lifecycle.example", is_platform_admin=True
        )
        await _make_user(
            db_session, tenant_d, email="guardrail-d@lifecycle.example", is_platform_admin=True
        )
        response = await client.patch(
            f"/api/v1/platform/tenants/{tenant_c.id}/status",
            json={"status": "suspended"},
            headers={"Authorization": f"Bearer {_token_for(admin_c)}"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "suspended"
