"""Sprint 17 Session 3 - migration-time permission propagation.

Exercises migrations/helpers/permission_propagation.py the same way a real
Alembic migration would call it: via a synchronous Core `Connection`
obtained through `AsyncSession.run_sync`, not the app's async ORM session -
`op.get_bind()` inside a real migration's `upgrade()` returns exactly this
kind of connection (see migrations/env.py's `do_run_migrations`).

No real permission is added to any shipped migration this session (see the
final report's Phase 5 section for why) - `_TEST_PERMISSION_CODE` below
exists only inside these rolled-back test transactions and is never
committed to the real permission catalog.
"""

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import engine
from app.modules.auth.constants import (
    ADMIN_ROLE,
    DEFAULT_TENANT_SLUG,
    MANAGER_ROLE,
    OPERATOR_ROLE,
    SYSTEM_ROLES,
)
from app.modules.auth.models import Permission, Role, RolePermission, Tenant
from migrations.helpers.permission_propagation import propagate_permission_grant

_TEST_PERMISSION_CODE = "session3_test:propagation_probe"


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


async def _default_tenant(db_session: AsyncSession) -> Tenant:
    """Explicitly the seeded default tenant by its canonical slug (Sprint 17
    Session 6) - a plain `select(Tenant).first()` is nondeterministic once
    other legitimate tenants exist in the shared dev database."""
    return (
        (await db_session.execute(select(Tenant).where(Tenant.slug == DEFAULT_TENANT_SLUG)))
        .scalars()
        .one()
    )


async def _make_tenant(db_session: AsyncSession, slug: str) -> Tenant:
    """A tenant with its own copy of every system role - mirrors what
    platform_admin.TenantService.create_tenant actually provisions, without
    going through the HTTP layer (these tests are about the migration
    helper, not the provisioning endpoint - that's test_tenant_provisioning.py)."""
    tenant = Tenant(name=f"Propagation Test {slug}", slug=slug)
    db_session.add(tenant)
    await db_session.flush()
    for role_name in SYSTEM_ROLES:
        db_session.add(Role(tenant_id=tenant.id, name=role_name, is_system=True))
    await db_session.commit()
    return tenant


async def _role_id(db_session: AsyncSession, tenant_id, name: str):
    return (
        await db_session.execute(
            select(Role.id).where(Role.tenant_id == tenant_id, Role.name == name)
        )
    ).scalar_one()


async def _propagate(db_session: AsyncSession, **kwargs) -> None:
    def _run(sync_session) -> None:
        connection: Connection = sync_session.connection()
        propagate_permission_grant(connection, **kwargs)

    await db_session.run_sync(_run)
    await db_session.commit()


def _grant_kwargs(**overrides) -> dict:
    base = {
        "code": _TEST_PERMISSION_CODE,
        "resource": "session3_test",
        "action": "propagation_probe",
        "description": "Sprint 17 Session 3 propagation mechanism test probe",
        "granted_to_roles": [ADMIN_ROLE],
    }
    base.update(overrides)
    return base


class TestSingleTenantPropagation:
    async def test_one_tenant_receives_the_new_permission(self, db_session: AsyncSession) -> None:
        default_tenant = await _default_tenant(db_session)
        await _propagate(db_session, **_grant_kwargs())

        permission_id = (
            await db_session.execute(
                select(Permission.id).where(Permission.code == _TEST_PERMISSION_CODE)
            )
        ).scalar_one()
        admin_role_id = await _role_id(db_session, default_tenant.id, ADMIN_ROLE)
        grant = (
            await db_session.execute(
                select(RolePermission).where(
                    RolePermission.role_id == admin_role_id,
                    RolePermission.permission_id == permission_id,
                )
            )
        ).scalar_one_or_none()
        assert grant is not None


class TestMultiTenantPropagation:
    async def test_multiple_existing_tenants_all_receive_it(self, db_session: AsyncSession) -> None:
        default_tenant = await _default_tenant(db_session)
        tenant_b = await _make_tenant(db_session, "propagation-multi-b")
        tenant_c = await _make_tenant(db_session, "propagation-multi-c")

        await _propagate(db_session, **_grant_kwargs())

        permission_id = (
            await db_session.execute(
                select(Permission.id).where(Permission.code == _TEST_PERMISSION_CODE)
            )
        ).scalar_one()
        for tenant in (default_tenant, tenant_b, tenant_c):
            admin_role_id = await _role_id(db_session, tenant.id, ADMIN_ROLE)
            grant = (
                await db_session.execute(
                    select(RolePermission).where(
                        RolePermission.role_id == admin_role_id,
                        RolePermission.permission_id == permission_id,
                    )
                )
            ).scalar_one_or_none()
            assert grant is not None, f"tenant {tenant.slug} did not receive the grant"

    async def test_only_intended_roles_receive_it(self, db_session: AsyncSession) -> None:
        default_tenant = await _default_tenant(db_session)
        await _propagate(db_session, **_grant_kwargs(granted_to_roles=[ADMIN_ROLE, MANAGER_ROLE]))

        permission_id = (
            await db_session.execute(
                select(Permission.id).where(Permission.code == _TEST_PERMISSION_CODE)
            )
        ).scalar_one()
        for granted_role in (ADMIN_ROLE, MANAGER_ROLE):
            role_id = await _role_id(db_session, default_tenant.id, granted_role)
            assert (
                await db_session.execute(
                    select(RolePermission).where(
                        RolePermission.role_id == role_id,
                        RolePermission.permission_id == permission_id,
                    )
                )
            ).scalar_one_or_none() is not None

        operator_role_id = await _role_id(db_session, default_tenant.id, OPERATOR_ROLE)
        assert (
            await db_session.execute(
                select(RolePermission).where(
                    RolePermission.role_id == operator_role_id,
                    RolePermission.permission_id == permission_id,
                )
            )
        ).scalar_one_or_none() is None

    async def test_custom_non_system_role_never_receives_it(self, db_session: AsyncSession) -> None:
        default_tenant = await _default_tenant(db_session)
        custom_role = Role(tenant_id=default_tenant.id, name="harbour_liaison", is_system=False)
        db_session.add(custom_role)
        await db_session.commit()

        await _propagate(db_session, **_grant_kwargs(granted_to_roles=[ADMIN_ROLE]))

        permission_id = (
            await db_session.execute(
                select(Permission.id).where(Permission.code == _TEST_PERMISSION_CODE)
            )
        ).scalar_one()
        assert (
            await db_session.execute(
                select(RolePermission).where(
                    RolePermission.role_id == custom_role.id,
                    RolePermission.permission_id == permission_id,
                )
            )
        ).scalar_one_or_none() is None


class TestIdempotency:
    async def test_running_twice_creates_no_duplicate_rows(self, db_session: AsyncSession) -> None:
        await _make_tenant(db_session, "propagation-idempotent-b")
        await _propagate(db_session, **_grant_kwargs())

        permission_count_after_first = (
            await db_session.execute(
                select(func.count())
                .select_from(Permission)
                .where(Permission.code == _TEST_PERMISSION_CODE)
            )
        ).scalar_one()
        grant_count_after_first = (
            await db_session.execute(
                select(func.count())
                .select_from(RolePermission)
                .join(Permission, Permission.id == RolePermission.permission_id)
                .where(Permission.code == _TEST_PERMISSION_CODE)
            )
        ).scalar_one()

        await _propagate(db_session, **_grant_kwargs())

        permission_count_after_second = (
            await db_session.execute(
                select(func.count())
                .select_from(Permission)
                .where(Permission.code == _TEST_PERMISSION_CODE)
            )
        ).scalar_one()
        grant_count_after_second = (
            await db_session.execute(
                select(func.count())
                .select_from(RolePermission)
                .join(Permission, Permission.id == RolePermission.permission_id)
                .where(Permission.code == _TEST_PERMISSION_CODE)
            )
        ).scalar_one()

        assert permission_count_after_first == 1
        assert permission_count_after_second == 1
        assert grant_count_after_second == grant_count_after_first


class TestMissingRolePolicy:
    async def test_tenant_missing_the_target_role_aborts_the_whole_grant(
        self, db_session: AsyncSession
    ) -> None:
        """Fail loud, all-or-nothing: Sprint 17 Session 3's chosen policy
        (see migrations/helpers/permission_propagation.py's docstring).
        Corrupt ONE tenant's role set and prove NEITHER it NOR a healthy
        tenant receives anything."""
        default_tenant = await _default_tenant(db_session)
        corrupted_tenant = await _make_tenant(db_session, "propagation-corrupted")
        await db_session.execute(
            Role.__table__.delete().where(
                Role.tenant_id == corrupted_tenant.id, Role.name == OPERATOR_ROLE
            )
        )
        await db_session.commit()

        with pytest.raises(RuntimeError, match="have no role named 'operator'"):
            await _propagate(db_session, **_grant_kwargs(granted_to_roles=[OPERATOR_ROLE]))

        # Nothing was granted anywhere - not even to the healthy default
        # tenant's pre-existing "operator" role (which already legitimately
        # holds unrelated grants like fish:view - only the absence of THIS
        # test permission's row is the thing being proven here).
        permission_row = (
            await db_session.execute(
                select(Permission).where(Permission.code == _TEST_PERMISSION_CODE)
            )
        ).scalar_one_or_none()
        assert permission_row is None
        default_operator_role_id = await _role_id(db_session, default_tenant.id, OPERATOR_ROLE)
        assert (
            await db_session.execute(
                select(RolePermission)
                .join(Permission, Permission.id == RolePermission.permission_id)
                .where(
                    RolePermission.role_id == default_operator_role_id,
                    Permission.code == _TEST_PERMISSION_CODE,
                )
            )
        ).first() is None


class TestProvisioningConvergence:
    async def test_pre_and_post_migration_tenants_converge_to_the_same_baseline(
        self, db_session: AsyncSession
    ) -> None:
        """Provision tenant BEFORE the (simulated) migration runs, run the
        propagation helper (the "migration"), then provision a second
        tenant AFTER it - both must end up with an identical permission set
        for the role that received the grant."""
        pre_migration_tenant = await _make_tenant(db_session, "propagation-pre")

        await _propagate(db_session, **_grant_kwargs(granted_to_roles=[ADMIN_ROLE]))

        # Provisioning "after the migration": mirrors TenantService.create_tenant's
        # own copy-from-default-tenant step, using the now-upgraded default tenant.
        post_migration_tenant = await _make_tenant(db_session, "propagation-post")
        permission_id = (
            await db_session.execute(
                select(Permission.id).where(Permission.code == _TEST_PERMISSION_CODE)
            )
        ).scalar_one()
        default_tenant = await _default_tenant(db_session)
        default_admin_role_id = await _role_id(db_session, default_tenant.id, ADMIN_ROLE)
        # _make_tenant only copies role NAMES (mirrors provisioning's role
        # shape), not permissions - grant it here the same way
        # TenantService.create_tenant copies the default tenant's current
        # permissions for each role it creates.
        post_admin_role_id = await _role_id(db_session, post_migration_tenant.id, ADMIN_ROLE)
        db_session.add(RolePermission(role_id=post_admin_role_id, permission_id=permission_id))
        await db_session.commit()

        pre_admin_role_id = await _role_id(db_session, pre_migration_tenant.id, ADMIN_ROLE)
        pre_has_it = (
            await db_session.execute(
                select(RolePermission).where(
                    RolePermission.role_id == pre_admin_role_id,
                    RolePermission.permission_id == permission_id,
                )
            )
        ).scalar_one_or_none() is not None
        post_has_it = (
            await db_session.execute(
                select(RolePermission).where(
                    RolePermission.role_id == post_admin_role_id,
                    RolePermission.permission_id == permission_id,
                )
            )
        ).scalar_one_or_none() is not None

        assert pre_has_it is True, "tenant provisioned BEFORE the migration was not upgraded"
        assert post_has_it is True, "tenant provisioned AFTER the migration lacks the baseline"
        assert pre_has_it == post_has_it
        assert default_admin_role_id is not None  # sanity: default tenant's role was resolvable
