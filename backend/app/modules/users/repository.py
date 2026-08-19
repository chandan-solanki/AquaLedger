import uuid
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.constants import ADMIN_ROLE, SUPER_ADMIN_ROLE, AccountStatus
from app.modules.auth.models import Role, User, UserRole

_SORT_COLUMNS: dict[str, Any] = {
    "full_name": User.full_name,
    "email": User.email,
    "username": User.username,
    "created_at": User.created_at,
    "last_login_at": User.last_login_at,
}

_ADMIN_ROLE_NAMES = (ADMIN_ROLE, SUPER_ADMIN_ROLE)


class UserRepository:
    """All raw queries for the users module live here - services never build SQL.

    Deliberately does not duplicate app.modules.auth.repository.AuthRepository
    (login/token/audit concerns); this is the admin-CRUD counterpart over the
    same User/Role/UserRole tables owned by the auth module.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> User | None:
        result = await self._session.execute(
            select(User)
            .where(User.id == user_id, User.tenant_id == tenant_id, User.deleted_at.is_(None))
            .options(selectinload(User.roles))
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        tenant_id: uuid.UUID,
        *,
        q: str | None,
        role_id: uuid.UUID | None,
        status: AccountStatus | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> tuple[list[User], int]:
        """Filtered, sorted, paginated user list plus the total match count.

        Two queries (count + page), tie-broken by id for stable pagination -
        mirrors CompanyRepository.search. A role_id filter joins user_roles;
        that join can't multiply rows since (user_id, role_id) is UserRole's
        composite primary key.
        """
        conditions = [User.tenant_id == tenant_id, User.deleted_at.is_(None)]
        if status is not None:
            conditions.append(User.status == status)
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            conditions.append(
                or_(
                    User.full_name.ilike(pattern),
                    User.email.ilike(pattern),
                    User.username.ilike(pattern),
                )
            )

        count_stmt = select(func.count()).select_from(User).where(*conditions)
        row_stmt = select(User).where(*conditions).options(selectinload(User.roles))

        if role_id is not None:
            count_stmt = (
                select(func.count(func.distinct(User.id)))
                .select_from(User)
                .join(UserRole, UserRole.user_id == User.id)
                .where(*conditions, UserRole.role_id == role_id)
            )
            row_stmt = (
                select(User)
                .join(UserRole, UserRole.user_id == User.id)
                .where(*conditions, UserRole.role_id == role_id)
                .options(selectinload(User.roles))
            )

        total = (await self._session.execute(count_stmt)).scalar_one()

        sort_field = sort[1:] if sort.startswith("-") else sort
        column = _SORT_COLUMNS[sort_field]
        order = column.desc() if sort.startswith("-") else column.asc()

        rows = (
            (
                await self._session.execute(
                    row_stmt.order_by(order, User.id)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def add(self, user: User) -> User:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits (and can catch the unique-
        constraint violation) as a single, deliberate step."""
        self._session.add(user)
        return user

    async def get_role_by_id(self, role_id: uuid.UUID, tenant_id: uuid.UUID) -> Role | None:
        result = await self._session.execute(
            select(Role).where(Role.id == role_id, Role.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list_roles(self, tenant_id: uuid.UUID) -> list[Role]:
        result = await self._session.execute(
            select(Role).where(Role.tenant_id == tenant_id).order_by(Role.name)
        )
        return list(result.scalars().all())

    async def set_role(
        self, user_id: uuid.UUID, role_id: uuid.UUID, *, assigned_by: uuid.UUID
    ) -> None:
        """Replaces every existing role assignment for this user with a
        single role. UserRole's schema supports many-to-many, but this
        module's UI only ever manages one role per user, matching the seed
        data's actual usage (ARCHITECTURE.md's role model, not a hard
        constraint) - a future Roles & Permissions session can extend this
        without a migration."""
        await self._session.execute(delete(UserRole).where(UserRole.user_id == user_id))
        self._session.add(UserRole(user_id=user_id, role_id=role_id, assigned_by=assigned_by))

    async def count_other_active_admins(
        self, tenant_id: uuid.UUID, *, exclude_user_id: uuid.UUID
    ) -> int:
        """Active (non-deleted, status=active) users other than
        exclude_user_id who are either is_superuser or hold the admin/
        super_admin role - used by UserService.set_status to block
        deactivating the last administrator standing for a tenant."""
        result = await self._session.execute(
            select(func.count(func.distinct(User.id)))
            .select_from(User)
            .outerjoin(UserRole, UserRole.user_id == User.id)
            .outerjoin(Role, Role.id == UserRole.role_id)
            .where(
                User.tenant_id == tenant_id,
                User.deleted_at.is_(None),
                User.status == AccountStatus.ACTIVE,
                User.id != exclude_user_id,
                or_(User.is_superuser.is_(True), Role.name.in_(_ADMIN_ROLE_NAMES)),
            )
        )
        return result.scalar_one()
