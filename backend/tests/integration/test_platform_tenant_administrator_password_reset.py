"""Sprint 17 Session 7 (post-review) - platform admin can reset a locked-out
tenant's administrator password.

Central claims under test: only a real platform admin can reach either
endpoint; the target must actually be an administrator (is_superuser or
admin/super_admin role) of the specific tenant named in the URL - never an
arbitrary tenant user, and never resolved against the wrong tenant; a
successful reset behaves exactly like UserService.reset_password (forces a
change on next login, revokes every existing session) and never mutates
is_superuser/is_platform_admin/roles; and the platform admin can never use
this to reset their own password.
"""

import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import engine, get_db
from app.main import app
from app.modules.auth.constants import ADMIN_ROLE, DEFAULT_TENANT_SLUG, AccountStatus
from app.modules.auth.models import AuditLog, Role, Tenant, User, UserRole
from app.modules.auth.security import create_access_token, hash_password

_PASSWORD = "Whatever@123"
_NEW_PASSWORD = "BrandNew@456"


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
    return (
        (await db_session.execute(select(Tenant).where(Tenant.slug == DEFAULT_TENANT_SLUG)))
        .scalars()
        .one()
    )


async def _make_tenant(db_session: AsyncSession, slug: str) -> Tenant:
    tenant = Tenant(name=f"Password Reset Test {slug}", slug=slug)
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
    role_name: str | None = None,
) -> User:
    user = User(
        tenant_id=tenant.id,
        email=email,
        username=email.split("@")[0],
        password_hash=hash_password(_PASSWORD),
        full_name="Password Reset Test User",
        status=AccountStatus.ACTIVE,
        is_superuser=is_superuser,
        is_platform_admin=is_platform_admin,
    )
    db_session.add(user)
    await db_session.flush()
    if role_name is not None:
        role = Role(tenant_id=tenant.id, name=role_name, is_system=False)
        db_session.add(role)
        await db_session.flush()
        db_session.add(UserRole(user_id=user.id, role_id=role.id, assigned_by=user.id))
    await db_session.commit()
    return user


def _token_for(user: User) -> str:
    return create_access_token(subject=user.id, tenant_id=user.tenant_id, roles=[], permissions=[])


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token_for(user)}"}


class TestListTenantAdministratorsAuthorization:
    async def test_platform_admin_can_list(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session, default_tenant, email="list-admins-pa@fisherp.local", is_platform_admin=True
        )
        target_tenant = await _make_tenant(db_session, "list-admins-target")
        await _make_user(
            db_session,
            target_tenant,
            email="list-admins-tenant-admin@fisherp.local",
            is_superuser=True,
        )

        response = await client.get(
            f"/api/v1/platform/tenants/{target_tenant.id}/administrators",
            headers=_auth_headers(platform_admin),
        )
        assert response.status_code == 200
        emails = {row["email"] for row in response.json()}
        assert "list-admins-tenant-admin@fisherp.local" in emails

    async def test_tenant_superuser_cannot_list(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        superuser = await _make_user(
            db_session,
            default_tenant,
            email="list-admins-superuser@fisherp.local",
            is_superuser=True,
        )
        response = await client.get(
            f"/api/v1/platform/tenants/{default_tenant.id}/administrators",
            headers=_auth_headers(superuser),
        )
        assert response.status_code == 403

    async def test_unknown_tenant_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session,
            default_tenant,
            email="list-admins-404-pa@fisherp.local",
            is_platform_admin=True,
        )
        response = await client.get(
            f"/api/v1/platform/tenants/{uuid.uuid4()}/administrators",
            headers=_auth_headers(platform_admin),
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TENANT_NOT_FOUND"


class TestListTenantAdministratorsContent:
    async def test_excludes_ordinary_tenant_users_and_inactive_admins(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session,
            default_tenant,
            email="list-admins-content-pa@fisherp.local",
            is_platform_admin=True,
        )
        target_tenant = await _make_tenant(db_session, "list-admins-content")
        active_admin = await _make_user(
            db_session, target_tenant, email="content-active-admin@fisherp.local", is_superuser=True
        )
        ordinary_user = await _make_user(
            db_session, target_tenant, email="content-ordinary-user@fisherp.local"
        )
        inactive_admin = await _make_user(
            db_session,
            target_tenant,
            email="content-inactive-admin@fisherp.local",
            is_superuser=True,
        )
        inactive_admin.status = AccountStatus.INACTIVE
        await db_session.commit()

        response = await client.get(
            f"/api/v1/platform/tenants/{target_tenant.id}/administrators",
            headers=_auth_headers(platform_admin),
        )
        assert response.status_code == 200
        returned_ids = {row["id"] for row in response.json()}
        assert str(active_admin.id) in returned_ids
        assert str(ordinary_user.id) not in returned_ids
        assert str(inactive_admin.id) not in returned_ids

    async def test_response_never_contains_password_or_role_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session,
            default_tenant,
            email="list-admins-shape-pa@fisherp.local",
            is_platform_admin=True,
        )
        target_tenant = await _make_tenant(db_session, "list-admins-shape")
        await _make_user(
            db_session, target_tenant, email="shape-admin@fisherp.local", is_superuser=True
        )

        response = await client.get(
            f"/api/v1/platform/tenants/{target_tenant.id}/administrators",
            headers=_auth_headers(platform_admin),
        )
        row = next(r for r in response.json() if r["email"] == "shape-admin@fisherp.local")
        assert set(row.keys()) == {"id", "email", "username", "full_name", "is_superuser", "status"}


class TestResetTenantAdministratorPasswordAuthorization:
    async def test_tenant_superuser_cannot_reset(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        actor = await _make_user(
            db_session,
            default_tenant,
            email="reset-auth-superuser@fisherp.local",
            is_superuser=True,
        )
        target_tenant = await _make_tenant(db_session, "reset-auth-target")
        target_admin = await _make_user(
            db_session,
            target_tenant,
            email="reset-auth-target-admin@fisherp.local",
            is_superuser=True,
        )

        response = await client.patch(
            f"/api/v1/platform/tenants/{target_tenant.id}/administrators/{target_admin.id}/password",
            json={"new_password": _NEW_PASSWORD},
            headers=_auth_headers(actor),
        )
        assert response.status_code == 403

    async def test_requires_authentication(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        target_tenant = await _make_tenant(db_session, "reset-auth-noauth")
        target_admin = await _make_user(
            db_session,
            target_tenant,
            email="reset-auth-noauth-admin@fisherp.local",
            is_superuser=True,
        )
        response = await client.patch(
            f"/api/v1/platform/tenants/{target_tenant.id}/administrators/{target_admin.id}/password",
            json={"new_password": _NEW_PASSWORD},
        )
        assert response.status_code == 401


class TestResetTenantAdministratorPasswordValidation:
    async def test_unknown_tenant_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session,
            default_tenant,
            email="reset-404-tenant-pa@fisherp.local",
            is_platform_admin=True,
        )
        response = await client.patch(
            f"/api/v1/platform/tenants/{uuid.uuid4()}/administrators/{uuid.uuid4()}/password",
            json={"new_password": _NEW_PASSWORD},
            headers=_auth_headers(platform_admin),
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TENANT_NOT_FOUND"

    async def test_ordinary_tenant_user_cannot_be_targeted(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session,
            default_tenant,
            email="reset-404-user-pa@fisherp.local",
            is_platform_admin=True,
        )
        target_tenant = await _make_tenant(db_session, "reset-404-user")
        ordinary_user = await _make_user(
            db_session, target_tenant, email="reset-404-ordinary@fisherp.local"
        )

        response = await client.patch(
            f"/api/v1/platform/tenants/{target_tenant.id}/administrators/{ordinary_user.id}/password",
            json={"new_password": _NEW_PASSWORD},
            headers=_auth_headers(platform_admin),
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TENANT_ADMINISTRATOR_NOT_FOUND"

    async def test_administrator_of_a_different_tenant_cannot_be_targeted(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session,
            default_tenant,
            email="reset-cross-tenant-pa@fisherp.local",
            is_platform_admin=True,
        )
        tenant_a = await _make_tenant(db_session, "reset-cross-tenant-a")
        tenant_b = await _make_tenant(db_session, "reset-cross-tenant-b")
        admin_of_b = await _make_user(
            db_session,
            tenant_b,
            email="reset-cross-tenant-admin-b@fisherp.local",
            is_superuser=True,
        )

        response = await client.patch(
            f"/api/v1/platform/tenants/{tenant_a.id}/administrators/{admin_of_b.id}/password",
            json={"new_password": _NEW_PASSWORD},
            headers=_auth_headers(platform_admin),
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TENANT_ADMINISTRATOR_NOT_FOUND"

    async def test_weak_password_is_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session,
            default_tenant,
            email="reset-weak-pw-pa@fisherp.local",
            is_platform_admin=True,
        )
        target_tenant = await _make_tenant(db_session, "reset-weak-pw")
        target_admin = await _make_user(
            db_session, target_tenant, email="reset-weak-pw-admin@fisherp.local", is_superuser=True
        )

        response = await client.patch(
            f"/api/v1/platform/tenants/{target_tenant.id}/administrators/{target_admin.id}/password",
            json={"new_password": "weak"},
            headers=_auth_headers(platform_admin),
        )
        assert response.status_code == 422
        assert "new_password" in response.json()["error"]["field_errors"]

    async def test_admin_role_holder_without_is_superuser_can_be_targeted(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session,
            default_tenant,
            email="reset-role-admin-pa@fisherp.local",
            is_platform_admin=True,
        )
        target_tenant = await _make_tenant(db_session, "reset-role-admin")
        role_admin = await _make_user(
            db_session,
            target_tenant,
            email="reset-role-admin-user@fisherp.local",
            role_name=ADMIN_ROLE,
        )

        response = await client.patch(
            f"/api/v1/platform/tenants/{target_tenant.id}/administrators/{role_admin.id}/password",
            json={"new_password": _NEW_PASSWORD},
            headers=_auth_headers(platform_admin),
        )
        assert response.status_code == 200


class TestResetTenantAdministratorPasswordSuccess:
    async def test_reset_forces_change_and_revokes_sessions(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session,
            default_tenant,
            email="reset-success-pa@fisherp.local",
            is_platform_admin=True,
        )
        target_tenant = await _make_tenant(db_session, "reset-success")
        target_admin = await _make_user(
            db_session, target_tenant, email="reset-success-admin@fisherp.local", is_superuser=True
        )

        # Establish a real session under the OLD password before resetting.
        old_login = await client.post(
            "/api/v1/auth/login",
            json={"email": target_admin.email, "password": _PASSWORD},
        )
        assert old_login.status_code == 200
        old_refresh_token = old_login.json()["refresh_token"]

        response = await client.patch(
            f"/api/v1/platform/tenants/{target_tenant.id}/administrators/{target_admin.id}/password",
            json={"new_password": _NEW_PASSWORD},
            headers=_auth_headers(platform_admin),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(target_admin.id)
        assert body["email"] == target_admin.email
        assert "password" not in body and "password_hash" not in body

        # The old session is dead.
        refresh_attempt = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": old_refresh_token}
        )
        assert refresh_attempt.status_code == 401

        # The old password no longer works.
        old_password_login = await client.post(
            "/api/v1/auth/login",
            json={"email": target_admin.email, "password": _PASSWORD},
        )
        assert old_password_login.status_code == 401

        # The new password works, and must_change_password is forced.
        new_password_login = await client.post(
            "/api/v1/auth/login",
            json={"email": target_admin.email, "password": _NEW_PASSWORD},
        )
        assert new_password_login.status_code == 200
        assert new_password_login.json()["must_change_password"] is True

    async def test_never_touches_is_superuser_or_is_platform_admin(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session, default_tenant, email="reset-flags-pa@fisherp.local", is_platform_admin=True
        )
        target_tenant = await _make_tenant(db_session, "reset-flags")
        target_admin = await _make_user(
            db_session, target_tenant, email="reset-flags-admin@fisherp.local", is_superuser=True
        )

        response = await client.patch(
            f"/api/v1/platform/tenants/{target_tenant.id}/administrators/{target_admin.id}/password",
            json={"new_password": _NEW_PASSWORD},
            headers=_auth_headers(platform_admin),
        )
        assert response.status_code == 200

        refreshed = (
            await db_session.execute(select(User).where(User.id == target_admin.id))
        ).scalar_one()
        assert refreshed.is_superuser is True
        assert refreshed.is_platform_admin is False

    async def test_cannot_reset_own_password_via_this_endpoint(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # A platform admin who also happens to be an administrator of the
        # tenant they are targeting (an edge case, not the normal shape)
        # still cannot use this endpoint on themselves.
        target_tenant = await _make_tenant(db_session, "reset-self")
        platform_admin_and_tenant_admin = await _make_user(
            db_session,
            target_tenant,
            email="reset-self-pa@fisherp.local",
            is_platform_admin=True,
            is_superuser=True,
        )

        response = await client.patch(
            f"/api/v1/platform/tenants/{target_tenant.id}/administrators/"
            f"{platform_admin_and_tenant_admin.id}/password",
            json={"new_password": _NEW_PASSWORD},
            headers=_auth_headers(platform_admin_and_tenant_admin),
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "CANNOT_RESET_OWN_PASSWORD"

    async def test_creates_audit_record_without_leaking_the_password(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session, default_tenant, email="reset-audit-pa@fisherp.local", is_platform_admin=True
        )
        target_tenant = await _make_tenant(db_session, "reset-audit")
        target_admin = await _make_user(
            db_session, target_tenant, email="reset-audit-admin@fisherp.local", is_superuser=True
        )

        response = await client.patch(
            f"/api/v1/platform/tenants/{target_tenant.id}/administrators/{target_admin.id}/password",
            json={"new_password": _NEW_PASSWORD},
            headers=_auth_headers(platform_admin),
        )
        assert response.status_code == 200

        audit_row = (
            await db_session.execute(
                select(AuditLog).where(
                    AuditLog.action == "tenant_administrator_password_reset",
                    AuditLog.entity_id == target_admin.id,
                )
            )
        ).scalar_one()
        assert audit_row.tenant_id == platform_admin.tenant_id
        assert audit_row.user_id == platform_admin.id
        assert audit_row.changes == {"tenant_id": str(target_tenant.id)}
        assert "password" not in str(audit_row.changes).lower()
