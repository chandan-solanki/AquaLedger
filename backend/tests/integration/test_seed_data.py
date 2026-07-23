from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Permission, Role, RolePermission, Tenant, User, UserRole


class TestSeededTenant:
    async def test_exactly_one_default_tenant(self, db_session: AsyncSession) -> None:
        count = (await db_session.execute(select(func.count()).select_from(Tenant))).scalar_one()
        assert count == 1

    async def test_default_tenant_shape(self, db_session: AsyncSession) -> None:
        tenant = (await db_session.execute(select(Tenant))).scalars().one()
        assert tenant.slug == "default"
        assert tenant.base_currency == "INR"
        assert 1 <= tenant.fiscal_year_start_month <= 12


class TestSeededRoles:
    async def test_five_system_roles_seeded(self, db_session: AsyncSession) -> None:
        names = (await db_session.execute(select(Role.name))).scalars().all()
        assert sorted(names) == ["accountant", "admin", "manager", "operator", "super_admin"]

    async def test_all_roles_are_marked_system(self, db_session: AsyncSession) -> None:
        is_system_flags = (await db_session.execute(select(Role.is_system))).scalars().all()
        assert all(is_system_flags)

    async def test_permission_counts_per_role_match_the_matrix(
        self, db_session: AsyncSession
    ) -> None:
        rows = (
            await db_session.execute(
                select(Role.name, func.count(RolePermission.permission_id))
                .join(RolePermission, RolePermission.role_id == Role.id)
                .group_by(Role.name)
            )
        ).all()
        counts: dict[str, int] = {row[0]: row[1] for row in rows}
        # Derived from ARCHITECTURE §9.2's role/permission matrix (Phase 2),
        # plus boat:create/edit/delete added for super_admin/admin/manager in
        # migration 72d5f6096c81 (Sprint 5 Session 2), plus trip:delete added
        # for super_admin/admin/manager in migration 244f758929a6
        # (Sprint 6 Session 2), plus trip_catch:view/create/edit/delete added
        # in migration d96d76e5af7a (Sprint 7 Session 2) - view also granted
        # to accountant, following the trip:view precedent - plus
        # trip_expense:view/create/edit/delete added in migration
        # f27a4c6e9b13 (Sprint 8 Session 2), same view-also-to-accountant
        # split, plus invoice:delete added for super_admin/admin/manager/
        # accountant in migration a1c9f7e3d5b2 (Sprint 9 Session 1) - unlike
        # the trip modules, accountant already held invoice:view/create/edit/
        # issue/cancel from the baseline seed, so it gets invoice:delete too.
        # Plus payment:create/edit/post added for super_admin/admin/manager/
        # accountant in migration 9d4c1f6a82e7 (Sprint 10 Session 1) - all
        # four already held payment:record from the baseline seed, the same
        # "already had the equivalent baseline permission" situation
        # invoice:delete's accountant grant was in.
        assert counts["super_admin"] == 47
        assert counts["admin"] == 47
        assert counts["manager"] == 41
        assert counts["accountant"] == 26
        assert counts["operator"] == 3

    async def test_operator_is_view_only(self, db_session: AsyncSession) -> None:
        codes = (
            (
                await db_session.execute(
                    select(Permission.code)
                    .join(RolePermission, RolePermission.permission_id == Permission.id)
                    .join(Role, Role.id == RolePermission.role_id)
                    .where(Role.name == "operator")
                )
            )
            .scalars()
            .all()
        )
        assert sorted(codes) == ["company:view", "fish:view", "invoice:view"]


class TestSeededPermissions:
    async def test_forty_seven_permissions_seeded(self, db_session: AsyncSession) -> None:
        count = (
            await db_session.execute(select(func.count()).select_from(Permission))
        ).scalar_one()
        assert count == 47

    async def test_permission_codes_are_unique(self, db_session: AsyncSession) -> None:
        codes = (await db_session.execute(select(Permission.code))).scalars().all()
        assert len(codes) == len(set(codes))

    async def test_permission_codes_follow_resource_colon_action(
        self, db_session: AsyncSession
    ) -> None:
        codes = (await db_session.execute(select(Permission.code))).scalars().all()
        assert all(":" in code for code in codes)


class TestSeededSuperAdmin:
    async def test_super_admin_user_exists_and_is_active(self, db_session: AsyncSession) -> None:
        user = (
            (await db_session.execute(select(User).where(User.email == "admin@fisherp.local")))
            .scalars()
            .one()
        )
        assert user.username == "admin"
        assert user.is_superuser is True
        assert user.status == AccountStatus.ACTIVE

    async def test_super_admin_has_the_super_admin_role(self, db_session: AsyncSession) -> None:
        user = (
            (await db_session.execute(select(User).where(User.email == "admin@fisherp.local")))
            .scalars()
            .one()
        )
        role_names = (
            (
                await db_session.execute(
                    select(Role.name)
                    .join(UserRole, UserRole.role_id == Role.id)
                    .where(UserRole.user_id == user.id)
                )
            )
            .scalars()
            .all()
        )
        assert role_names == ["super_admin"]

    async def test_super_admin_password_hash_is_not_plaintext(
        self, db_session: AsyncSession
    ) -> None:
        user = (
            (await db_session.execute(select(User).where(User.email == "admin@fisherp.local")))
            .scalars()
            .one()
        )
        assert user.password_hash != "Admin@123"
        assert user.password_hash.startswith("$argon2")
