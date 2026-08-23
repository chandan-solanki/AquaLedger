from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import DEFAULT_TENANT_SLUG, AccountStatus
from app.modules.auth.models import Permission, Role, RolePermission, Tenant, User, UserRole

# Sprint 17 Session 6: every permission code known to be legitimately seeded
# as of this session (78 total - grown from the 63 this file originally
# asserted an exact count for, via every module added since). This is a
# required *baseline*, checked with `.issubset()` below, not an exact-count
# assertion - the permission catalog is expected to keep growing as new
# modules ship, and a new module's migration adding new codes must never
# fail this test. What this DOES still catch: a migration or manual change
# accidentally deleting/renaming a previously-seeded permission.
_REQUIRED_PERMISSION_CODES = frozenset(
    {
        "audit_log:view",
        "boat:create",
        "boat:delete",
        "boat:edit",
        "boat:view",
        "boat_report:profit",
        "company:create",
        "company:delete",
        "company:edit",
        "company:view",
        "company:view_credit",
        "dashboard:view",
        "delivery_challan:cancel",
        "delivery_challan:create",
        "delivery_challan:delete",
        "delivery_challan:deliver",
        "delivery_challan:dispatch",
        "delivery_challan:edit",
        "delivery_challan:view",
        "document:view",
        "expense:approve",
        "expense:create",
        "expense:view",
        "fish:manage",
        "fish:view",
        "invoice:cancel",
        "invoice:create",
        "invoice:delete",
        "invoice:edit",
        "invoice:issue",
        "invoice:view",
        "payment:bounce",
        "payment:create",
        "payment:delete",
        "payment:edit",
        "payment:post",
        "payment:record",
        "payment:view",
        "purchase:create",
        "purchase:delete",
        "purchase:edit",
        "purchase:post",
        "purchase:view",
        "purchase_order:cancel",
        "purchase_order:confirm",
        "purchase_order:create",
        "purchase_order:delete",
        "purchase_order:edit",
        "purchase_order:fulfill",
        "purchase_order:view",
        "report:outstanding",
        "report:profit",
        "report:sales",
        "reports:view",
        "settings:manage",
        "supplier:create",
        "supplier:delete",
        "supplier:edit",
        "supplier:view",
        "supplier_payment:create",
        "supplier_payment:delete",
        "supplier_payment:edit",
        "supplier_payment:post",
        "supplier_payment:view",
        "trip:close",
        "trip:create",
        "trip:delete",
        "trip:edit",
        "trip:view",
        "trip_catch:create",
        "trip_catch:delete",
        "trip_catch:edit",
        "trip_catch:view",
        "trip_expense:create",
        "trip_expense:delete",
        "trip_expense:edit",
        "trip_expense:view",
        "user:manage",
    }
)


async def _default_tenant(db_session: AsyncSession) -> Tenant:
    """Explicitly the seeded default tenant by its canonical slug (Sprint 17
    Session 6) - a plain `select(Tenant).first()` is nondeterministic once
    other legitimate tenants exist in the shared dev database, and every
    assertion in this file is specifically about the *default* tenant's
    seed state, never about the database containing nothing else."""
    return (
        (await db_session.execute(select(Tenant).where(Tenant.slug == DEFAULT_TENANT_SLUG)))
        .scalars()
        .one()
    )


class TestSeededTenant:
    async def test_default_tenant_exists(self, db_session: AsyncSession) -> None:
        """Sprint 17 Session 6: the required invariant is that the default
        tenant exists (and is unique by its slug's own unique constraint) -
        not that it is the *only* tenant in the database. Multi-tenant is a
        real, supported feature (Sprint 17's platform-admin/tenant-
        provisioning work), so legitimate additional tenants - manually
        provisioned or created by other tests - must never fail this test."""
        tenant = await _default_tenant(db_session)
        assert tenant.slug == DEFAULT_TENANT_SLUG

    async def test_default_tenant_shape(self, db_session: AsyncSession) -> None:
        tenant = await _default_tenant(db_session)
        assert tenant.slug == "default"
        assert tenant.base_currency == "INR"
        assert 1 <= tenant.fiscal_year_start_month <= 12


class TestSeededRoles:
    async def test_five_system_roles_seeded(self, db_session: AsyncSession) -> None:
        """Scoped to the default tenant's own roles (Sprint 17 Session 6) -
        roles are tenant-scoped, and provisioning a new tenant (Sprint 17
        Session 2) replicates these same 5 role names into it, so an
        unscoped query would see 5 * (tenant count) rows once any other
        tenant has been provisioned."""
        default_tenant = await _default_tenant(db_session)
        names = (
            (await db_session.execute(select(Role.name).where(Role.tenant_id == default_tenant.id)))
            .scalars()
            .all()
        )
        assert sorted(names) == ["accountant", "admin", "manager", "operator", "super_admin"]

    async def test_all_roles_are_marked_system(self, db_session: AsyncSession) -> None:
        # Deliberately unscoped: every role in every tenant (including ones
        # replicated during provisioning) must be is_system - this is an
        # invariant of role provisioning itself, not just the default
        # tenant's seed state, so more tenants only make this check stronger.
        is_system_flags = (await db_session.execute(select(Role.is_system))).scalars().all()
        assert all(is_system_flags)

    async def test_permission_counts_per_role_match_the_matrix(
        self, db_session: AsyncSession
    ) -> None:
        default_tenant = await _default_tenant(db_session)
        rows = (
            await db_session.execute(
                select(Role.name, func.count(RolePermission.permission_id))
                .join(RolePermission, RolePermission.role_id == Role.id)
                .where(Role.tenant_id == default_tenant.id)
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
        # Plus the full supplier:view/create/edit/delete and purchase:view/
        # create/edit/delete/post surface (9 new codes) added for
        # super_admin/admin/manager/accountant in migration
        # 578d0e205274 (Sprint 11 Session 1) - unlike every prior module,
        # none of these codes existed in any earlier seed, so all 9 are new
        # to every one of those four roles' counts.
        # Plus the full supplier_payment:view/create/edit/delete/post surface
        # (5 new codes) added for super_admin/admin/manager/accountant in
        # migration 005c4ade9277 (Sprint 12 Session 1) - same as-new-to-
        # every-role situation supplier:*/purchase:* was in.
        # Plus dashboard:view (1 new code) added for super_admin/admin/
        # manager/accountant in migration e5c202771a70 (Sprint 10 Session 1
        # dashboard module) - the same four-role grant list as purchase/
        # supplier_payment, operator excluded for the same reason.
        # Plus reports:view (1 new code) added for super_admin/admin/
        # manager/accountant in migration b8d1f4a726c9 (Sprint 11 Session 1
        # reports module) - mirrors e5c202771a70's own grant list exactly,
        # operator excluded for the same reason.
        #
        # Sprint 17 Session 6: the totals above stopped being tracked
        # per-migration at some point after Sprint 12 (delivery_challan,
        # purchase_order, expense, boat_report, report:profit/sales/
        # outstanding, document:view, settings:manage, user:manage and
        # audit_log:view were all added since without updating this
        # assertion), so the counts below are verified directly against the
        # default tenant's live seed state rather than re-derived by hand.
        # super_admin/admin still hold the full permission catalog (78/78);
        # operator remains untouched at 3 (view-only, unaffected by any
        # module added after the original baseline).
        assert counts["super_admin"] == 78
        assert counts["admin"] == 78
        assert counts["manager"] == 72
        assert counts["accountant"] == 57
        assert counts["operator"] == 3

    async def test_operator_is_view_only(self, db_session: AsyncSession) -> None:
        default_tenant = await _default_tenant(db_session)
        codes = (
            (
                await db_session.execute(
                    select(Permission.code)
                    .join(RolePermission, RolePermission.permission_id == Permission.id)
                    .join(Role, Role.id == RolePermission.role_id)
                    .where(Role.name == "operator", Role.tenant_id == default_tenant.id)
                )
            )
            .scalars()
            .all()
        )
        assert sorted(codes) == ["company:view", "fish:view", "invoice:view"]


class TestSeededPermissions:
    async def test_required_baseline_permissions_are_seeded(self, db_session: AsyncSession) -> None:
        """Sprint 17 Session 6: replaces an exact-count assertion (`== 63`,
        later drifted to a real 78 across many un-tracked sprints) with a
        required-baseline check. The permission catalog is global (never
        tenant-scoped, never duplicated by tenant provisioning) and
        legitimately grows with every new module - the invariant worth
        testing is that a previously-seeded permission is never silently
        dropped, not an exact total every future module has to remember to
        bump here."""
        codes = set((await db_session.execute(select(Permission.code))).scalars().all())
        missing = _REQUIRED_PERMISSION_CODES - codes
        assert not missing, f"required permission code(s) missing: {sorted(missing)}"

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
        default_tenant = await _default_tenant(db_session)
        role_names = (
            (
                await db_session.execute(
                    select(Role.name)
                    .join(UserRole, UserRole.role_id == Role.id)
                    .where(UserRole.user_id == user.id, Role.tenant_id == default_tenant.id)
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
