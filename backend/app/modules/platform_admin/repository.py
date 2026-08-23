import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.constants import AccountStatus, TenantStatus
from app.modules.auth.models import Role, RolePermission, Tenant, User, UserRole

# Every module in this codebase queries auth.models' shared tables directly
# (roles/repository.py does exactly this for Role/Permission/User) rather
# than routing through AuthRepository for everything - Tenant has no
# dedicated module of its own, so platform_admin owns tenant-provisioning
# queries the same way.


class TenantRepository:
    """All raw queries for tenant provisioning/lifecycle live here - the
    roles module's RoleRepository is documented read-only by contract
    (Sprint 17 Session 1/2 audits), so this is a separate, write-capable
    repository rather than an exception carved into that one."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_tenant_by_slug(self, slug: str) -> Tenant | None:
        result = await self._session.execute(select(Tenant).where(Tenant.slug == slug))
        return result.scalar_one_or_none()

    async def get_tenant_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        result = await self._session.execute(select(Tenant).where(Tenant.id == tenant_id))
        return result.scalar_one_or_none()

    async def list_tenants(
        self, *, q: str | None, status: TenantStatus | None, page: int, page_size: int
    ) -> tuple[list[Tenant], int]:
        conditions = []
        if q:
            like = f"%{q.strip()}%"
            conditions.append(or_(Tenant.name.ilike(like), Tenant.slug.ilike(like)))
        if status is not None:
            conditions.append(Tenant.status == status)

        count_result = await self._session.execute(
            select(func.count()).select_from(Tenant).where(*conditions)
        )
        total = count_result.scalar_one()

        result = await self._session.execute(
            select(Tenant)
            .where(*conditions)
            # `id.desc()` is a stable tiebreaker for rows created in the same
            # transaction/instant (created_at collapses to identical values
            # there) - safe because every id is a time-ordered uuid7.
            .order_by(Tenant.created_at.desc(), Tenant.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    def add_tenant(self, tenant: Tenant) -> None:
        self._session.add(tenant)

    async def list_roles_with_permissions(self, tenant_id: uuid.UUID) -> list[Role]:
        """The live "what does a fully-provisioned tenant's role set look
        like" answer (Sprint 17 Session 2) - read from the default tenant's
        actual rows rather than a second hardcoded copy of migration seed
        data, so it can never drift from whatever migrations have done."""
        result = await self._session.execute(
            select(Role)
            .where(Role.tenant_id == tenant_id)
            .options(selectinload(Role.permissions))
            .order_by(Role.name)
        )
        return list(result.scalars().all())

    def add_role(self, role: Role) -> None:
        self._session.add(role)

    def add_role_permissions(self, role_permissions: list[RolePermission]) -> None:
        self._session.add_all(role_permissions)

    def add_user(self, user: User) -> None:
        self._session.add(user)

    def add_user_role(self, user_role: UserRole) -> None:
        self._session.add(user_role)

    async def count_tenants_by_status(self) -> dict[TenantStatus, int]:
        """Powers GET /platform/dashboard's summary cards - one grouped
        aggregate query rather than four separate `list_tenants` counts."""
        result = await self._session.execute(
            select(Tenant.status, func.count(Tenant.id)).group_by(Tenant.status)
        )
        counts = dict.fromkeys(TenantStatus, 0)
        for status, count in result.all():
            counts[TenantStatus(status)] = count
        return counts

    async def count_platform_admins_in_active_tenants(
        self, *, excluding_tenant_id: uuid.UUID
    ) -> int:
        """Reachable platform admins if `excluding_tenant_id` were no longer
        ACTIVE - used by the tenant-status-change guardrail (Phase 6) to
        refuse a transition that would leave none. "Reachable" mirrors
        UserRepository.count_other_active_admins' own definition of a live
        administrator: not soft-deleted, status=ACTIVE, and - the new
        condition here - belonging to a tenant that is itself ACTIVE."""
        result = await self._session.execute(
            select(func.count(User.id))
            .join(Tenant, Tenant.id == User.tenant_id)
            .where(
                User.is_platform_admin.is_(True),
                User.deleted_at.is_(None),
                User.status == AccountStatus.ACTIVE,
                Tenant.status == TenantStatus.ACTIVE,
                Tenant.id != excluding_tenant_id,
            )
        )
        return result.scalar_one()
