"""Sprint 17 Session 2 - tenant provisioning.

Mirrors tests/integration/test_platform_admin.py's helper style (Session 1).
Central claims under test: provisioning is fully transactional (any failure
leaves no tenant/role/user behind), the new tenant's roles/permissions are
replicated from the live default tenant (not a hardcoded copy), the initial
administrator gets is_superuser=True + role="admin" but never
is_platform_admin, and audit records never carry secrets.
"""

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.common.request_context import RequestContext
from app.db.session import engine, get_db
from app.main import app
from app.modules.auth.constants import DEFAULT_TENANT_SLUG, AccountStatus
from app.modules.auth.models import AuditLog, Role, RolePermission, Tenant, User, UserRole
from app.modules.auth.security import create_access_token, hash_password
from app.modules.platform_admin.exceptions import DuplicateTenantSlugError
from app.modules.platform_admin.schemas import TenantCreateRequest
from app.modules.platform_admin.service import TenantService
from app.modules.users.exceptions import DuplicateUserEmailError, DuplicateUsernameError


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
        full_name="Provisioning Test User",
        status=AccountStatus.ACTIVE,
        is_superuser=is_superuser,
        is_platform_admin=is_platform_admin,
    )
    db_session.add(user)
    await db_session.commit()
    return user


def _token_for(user: User) -> str:
    return create_access_token(subject=user.id, tenant_id=user.tenant_id, roles=[], permissions=[])


def _tenant_payload(slug: str, *, admin_email: str, admin_username: str) -> dict:
    return {
        "name": "Ocean Fresh Traders",
        "slug": slug,
        "plan": None,
        "base_currency": "INR",
        "fiscal_year_start_month": 4,
        "administrator": {
            "email": admin_email,
            "username": admin_username,
            "full_name": "Priya Nair",
            "password": "TempPass@123",
        },
    }


class TestCreateTenantAuthorization:
    async def test_unauthenticated_denied(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/platform/tenants",
            json=_tenant_payload("auth-test-1", admin_email="a@x.com", admin_username="a"),
        )
        assert response.status_code == 401

    async def test_normal_user_denied(self, client: AsyncClient, db_session: AsyncSession) -> None:
        tenant = await _default_tenant(db_session)
        user = await _make_user(db_session, tenant, email="prov-normal@fisherp.local")
        response = await client.post(
            "/api/v1/platform/tenants",
            json=_tenant_payload("auth-test-2", admin_email="a@x.com", admin_username="a2"),
            headers={"Authorization": f"Bearer {_token_for(user)}"},
        )
        assert response.status_code == 403

    async def test_tenant_superuser_denied(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _default_tenant(db_session)
        superuser = await _make_user(
            db_session, tenant, email="prov-superuser@fisherp.local", is_superuser=True
        )
        response = await client.post(
            "/api/v1/platform/tenants",
            json=_tenant_payload("auth-test-3", admin_email="a@x.com", admin_username="a3"),
            headers={"Authorization": f"Bearer {_token_for(superuser)}"},
        )
        assert response.status_code == 403


class TestCreateTenantSuccess:
    async def test_platform_admin_can_provision_a_fully_working_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        default_roles = (
            (await db_session.execute(select(Role).where(Role.tenant_id == default_tenant.id)))
            .scalars()
            .all()
        )
        default_role_names = {r.name for r in default_roles}

        platform_admin = await _make_user(
            db_session,
            default_tenant,
            email="prov-platform-admin@fisherp.local",
            is_platform_admin=True,
        )
        payload = _tenant_payload(
            "session2-success-tenant",
            admin_email="owner@session2.example",
            admin_username="session2owner",
        )
        response = await client.post(
            "/api/v1/platform/tenants",
            json=payload,
            headers={"Authorization": f"Bearer {_token_for(platform_admin)}"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["tenant"]["slug"] == "session2-success-tenant"
        assert body["tenant"]["status"] == "active"
        assert body["tenant"]["base_currency"] == "INR"
        assert body["administrator"]["email"] == "owner@session2.example"
        new_tenant_id = uuid.UUID(body["tenant"]["id"])
        admin_id = uuid.UUID(body["administrator"]["id"])

        # Required system roles were provisioned, matching the default tenant's set.
        new_roles = (
            (await db_session.execute(select(Role).where(Role.tenant_id == new_tenant_id)))
            .scalars()
            .all()
        )
        assert {r.name for r in new_roles} == default_role_names

        # Permissions were correctly attached: same per-role permission
        # counts as the default tenant.
        for role in new_roles:
            default_role = next(r for r in default_roles if r.name == role.name)
            new_count = (
                (
                    await db_session.execute(
                        select(RolePermission).where(RolePermission.role_id == role.id)
                    )
                )
                .scalars()
                .all()
            )
            default_count = (
                (
                    await db_session.execute(
                        select(RolePermission).where(RolePermission.role_id == default_role.id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(new_count) == len(default_count)

        # The initial administrator: is_superuser=True, "admin" role, never platform admin.
        admin_row = (await db_session.execute(select(User).where(User.id == admin_id))).scalar_one()
        assert admin_row.is_superuser is True
        assert admin_row.is_platform_admin is False

        assigned_role_id = (
            await db_session.execute(select(UserRole.role_id).where(UserRole.user_id == admin_id))
        ).scalar_one()
        assigned_role = next(r for r in new_roles if r.id == assigned_role_id)
        assert assigned_role.name == "admin"

        # The initial administrator can actually log in through the real flow.
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "owner@session2.example", "password": "TempPass@123"},
        )
        assert login_response.status_code == 200
        assert login_response.json()["user"]["is_superuser"] is True
        assert login_response.json()["user"]["is_platform_admin"] is False

        # Audit record: correct actor/target, no secrets.
        audit_row = (
            await db_session.execute(
                select(AuditLog).where(
                    AuditLog.action == "tenant_created", AuditLog.entity_id == new_tenant_id
                )
            )
        ).scalar_one()
        assert (
            audit_row.tenant_id == platform_admin.tenant_id
        )  # actor's own tenant, not the new one
        assert audit_row.user_id == platform_admin.id
        assert audit_row.changes is not None
        dumped = str(audit_row.changes)
        assert "TempPass@123" not in dumped
        assert "password" not in dumped.lower()


class TestCreateTenantRollback:
    async def test_duplicate_slug_leaves_no_partial_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session,
            default_tenant,
            email="prov-dup-slug-admin@fisherp.local",
            is_platform_admin=True,
        )
        headers = {"Authorization": f"Bearer {_token_for(platform_admin)}"}

        first = await client.post(
            "/api/v1/platform/tenants",
            json=_tenant_payload(
                "duplicate-slug-tenant", admin_email="first@dup.example", admin_username="firstdup"
            ),
            headers=headers,
        )
        assert first.status_code == 201

        second = await client.post(
            "/api/v1/platform/tenants",
            json=_tenant_payload(
                "duplicate-slug-tenant",
                admin_email="second@dup.example",
                admin_username="seconddup",
            ),
            headers=headers,
        )
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "DUPLICATE_TENANT_SLUG"

        tenants = (
            (await db_session.execute(select(Tenant).where(Tenant.slug == "duplicate-slug-tenant")))
            .scalars()
            .all()
        )
        assert len(tenants) == 1
        second_admin = (
            await db_session.execute(select(User).where(User.email == "second@dup.example"))
        ).scalar_one_or_none()
        assert second_admin is None

    async def test_forced_failure_after_role_provisioning_leaves_no_orphaned_data(
        self, db_session: AsyncSession
    ) -> None:
        """Directly exercises TenantService (not HTTP) to force a failure
        after roles are provisioned but before the admin user is created -
        proves the explicit try/except/rollback covers the whole operation,
        not just the final commit."""
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session,
            default_tenant,
            email="prov-forced-fail-admin@fisherp.local",
            is_platform_admin=True,
        )
        service = TenantService(db_session)
        payload = TenantCreateRequest.model_validate(
            _tenant_payload(
                "forced-failure-tenant",
                admin_email="forced@fail.example",
                admin_username="forcedfail",
            )
        )
        ctx = RequestContext(ip=None, user_agent=None, request_id=None)

        role_count_before = (
            await db_session.execute(select(func.count()).select_from(Role))
        ).scalar_one()

        # Force the failure at the add_user step, after role provisioning has
        # already flushed 5 new Role rows (+ their RolePermission rows) for
        # this new tenant within the same still-open transaction.
        with patch(
            "app.modules.platform_admin.repository.TenantRepository.add_user",
            side_effect=RuntimeError("forced provisioning failure"),
        ):
            with pytest.raises(RuntimeError, match="forced provisioning failure"):
                await service.create_tenant(payload, actor=platform_admin, ctx=ctx)

        orphaned_tenant = (
            await db_session.execute(select(Tenant).where(Tenant.slug == "forced-failure-tenant"))
        ).scalar_one_or_none()
        assert orphaned_tenant is None

        role_count_after = (
            await db_session.execute(select(func.count()).select_from(Role))
        ).scalar_one()
        assert role_count_after == role_count_before


class TestTranslateIntegrityError:
    """Tenant-scoped uniqueness (tenant_id, lower(email)) means two
    independent tenant-creation calls can never collide on the
    administrator's email/username - each new tenant gets a fresh
    tenant_id, so the partial unique index never fires across tenants (this
    was verified during the Session 2 audit, not assumed). These two
    branches of _translate_integrity_error are therefore tested directly
    against a constructed IntegrityError rather than via a real duplicate
    HTTP request, which would be structurally impossible to trigger between
    two different tenants."""

    def _fake_integrity_error(self, constraint_name: str) -> IntegrityError:
        driver_error = type("DriverError", (), {"constraint_name": constraint_name})()
        orig = type("Orig", (), {"__cause__": driver_error})()
        return IntegrityError("stmt", {}, orig)  # type: ignore[arg-type]

    def test_duplicate_email_constraint_maps_to_duplicate_user_email_error(self) -> None:
        exc = self._fake_integrity_error("ix_users_tenant_email")
        result = TenantService._translate_integrity_error(exc)
        assert isinstance(result, DuplicateUserEmailError)

    def test_duplicate_username_constraint_maps_to_duplicate_username_error(self) -> None:
        exc = self._fake_integrity_error("ix_users_tenant_username")
        result = TenantService._translate_integrity_error(exc)
        assert isinstance(result, DuplicateUsernameError)

    def test_duplicate_slug_constraint_maps_to_duplicate_tenant_slug_error(self) -> None:
        exc = self._fake_integrity_error("tenants_slug_key")
        result = TenantService._translate_integrity_error(exc)
        assert isinstance(result, DuplicateTenantSlugError)


class TestProvisioningBaselineIntegrity:
    """Sprint 17 Session 3 (Phase 6): the default tenant is kept as the
    authoritative source for provisioning, which is only safe if a
    corrupted default-tenant baseline can never be silently replicated.
    """

    async def test_provisioning_fails_loudly_when_default_tenant_is_missing_a_system_role(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session,
            default_tenant,
            email="prov-corrupted-baseline-admin@fisherp.local",
            is_platform_admin=True,
        )
        # Corrupt the baseline: delete the default tenant's "operator" role.
        # The real dev database accumulates users/role_permissions
        # referencing it over time, so every FK pointing at it must be
        # cleared first, not just role_permissions.
        operator_role_id = (
            await db_session.execute(
                select(Role.id).where(Role.tenant_id == default_tenant.id, Role.name == "operator")
            )
        ).scalar_one()
        await db_session.execute(
            UserRole.__table__.delete().where(UserRole.role_id == operator_role_id)
        )
        await db_session.execute(
            RolePermission.__table__.delete().where(RolePermission.role_id == operator_role_id)
        )
        await db_session.execute(Role.__table__.delete().where(Role.id == operator_role_id))
        await db_session.commit()

        response = await client.post(
            "/api/v1/platform/tenants",
            json=_tenant_payload(
                "corrupted-baseline-tenant",
                admin_email="corrupted@baseline.example",
                admin_username="corruptedbaseline",
            ),
            headers={"Authorization": f"Bearer {_token_for(platform_admin)}"},
        )
        assert response.status_code == 500

        orphaned_tenant = (
            await db_session.execute(
                select(Tenant).where(Tenant.slug == "corrupted-baseline-tenant")
            )
        ).scalar_one_or_none()
        assert orphaned_tenant is None

    async def test_provisioning_copies_exactly_the_default_tenants_permission_sets(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Stronger than the count-based check in TestCreateTenantSuccess:
        compares the actual PERMISSION CODE SETS per role, not just counts -
        closes the gap where counts could match by coincidence while the
        actual permissions differed."""
        default_tenant = await _default_tenant(db_session)
        platform_admin = await _make_user(
            db_session,
            default_tenant,
            email="prov-exact-match-admin@fisherp.local",
            is_platform_admin=True,
        )
        response = await client.post(
            "/api/v1/platform/tenants",
            json=_tenant_payload(
                "exact-match-tenant", admin_email="exact@match.example", admin_username="exactmatch"
            ),
            headers={"Authorization": f"Bearer {_token_for(platform_admin)}"},
        )
        assert response.status_code == 201
        new_tenant_id = uuid.UUID(response.json()["tenant"]["id"])

        from app.modules.auth.models import Permission

        async def _permission_codes_by_role(tenant_id: uuid.UUID) -> dict[str, set[str]]:
            rows = (
                await db_session.execute(
                    select(Role.name, Permission.code)
                    .join(RolePermission, RolePermission.role_id == Role.id)
                    .join(Permission, Permission.id == RolePermission.permission_id)
                    .where(Role.tenant_id == tenant_id)
                )
            ).all()
            result: dict[str, set[str]] = {}
            for role_name, code in rows:
                result.setdefault(role_name, set()).add(code)
            return result

        default_codes = await _permission_codes_by_role(default_tenant.id)
        new_codes = await _permission_codes_by_role(new_tenant_id)
        assert new_codes == default_codes
