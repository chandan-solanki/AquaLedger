import math
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.request_context import RequestContext
from app.common.schemas import PaginatedResponse, PaginationMeta
from app.core.errors import AppException, ConflictError, ValidationError
from app.modules.auth.constants import ADMIN_ROLE, SUPER_ADMIN_ROLE, AccountStatus
from app.modules.auth.exceptions import UserNotFoundError
from app.modules.auth.models import Role, User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.security import hash_password, password_policy_violations
from app.modules.users.exceptions import (
    CannotDeactivateLastAdminError,
    CannotDeactivateSelfError,
    DuplicateUserEmailError,
    DuplicateUsernameError,
    RoleNotFoundError,
    SuperAdminRoleProtectedError,
)
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import (
    RoleSummary,
    UserCreateRequest,
    UserListParams,
    UserResponse,
    UserUpdateRequest,
)


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = UserRepository(session)
        self._auth_repo = AuthRepository(session)

    async def create(
        self,
        payload: UserCreateRequest,
        *,
        tenant_id: uuid.UUID,
        actor: User,
        ctx: RequestContext,
    ) -> UserResponse:
        violations = password_policy_violations(payload.password)
        if violations:
            raise ValidationError(
                "Password does not meet policy requirements",
                field_errors={"password": violations},
            )

        role = await self._get_role_or_raise(payload.role_id, tenant_id)
        self._guard_super_admin_assignment(role, actor)

        user = User(
            tenant_id=tenant_id,
            email=payload.email,
            username=payload.username,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            phone=payload.phone,
            status=AccountStatus.ACTIVE,
            is_superuser=False,
            # password_changed_at stays null on purpose: AuthService treats
            # that as must_change_password=True on the account's first login.
        )
        await self._repo.add(user)
        await self._commit_or_raise()
        await self._session.refresh(user)

        await self._repo.set_role(user.id, role.id, assigned_by=actor.id)
        await self._auth_repo.add_audit_log(
            tenant_id=tenant_id,
            user_id=actor.id,
            action="user_created",
            entity_id=user.id,
            changes={"email": user.email, "username": user.username, "role": role.name},
            ip_address=ctx.ip,
            user_agent=ctx.user_agent,
            request_id=ctx.request_id,
        )
        await self._session.commit()
        self._session.expire(user, ["roles"])

        return await self._load_response(user.id, tenant_id)

    async def get(self, user_id: uuid.UUID, *, tenant_id: uuid.UUID) -> UserResponse:
        return await self._load_response(user_id, tenant_id)

    async def list_users(
        self, *, tenant_id: uuid.UUID, params: UserListParams
    ) -> PaginatedResponse[UserResponse]:
        users, total = await self._repo.search(
            tenant_id,
            q=params.q,
            role_id=params.role_id,
            status=params.status,
            sort=params.sort,
            page=params.page,
            page_size=params.page_size,
        )
        total_pages = math.ceil(total / params.page_size) if total else 0
        meta = PaginationMeta(
            total_records=total,
            total_pages=total_pages,
            current_page=params.page,
            page_size=params.page_size,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        )
        return PaginatedResponse(data=[self._to_response(user) for user in users], meta=meta)

    async def update(
        self,
        user_id: uuid.UUID,
        payload: UserUpdateRequest,
        *,
        tenant_id: uuid.UUID,
        actor: User,
        ctx: RequestContext,
    ) -> UserResponse:
        user = await self._get_or_raise(user_id, tenant_id)

        new_role: Role | None = None
        previous_role_name: str | None = None
        if payload.role_id is not None:
            new_role = await self._get_role_or_raise(payload.role_id, tenant_id)
            self._guard_super_admin_assignment(new_role, actor)
            self._guard_super_admin_revocation(user, actor)
            previous_role_name = user.roles[0].name if user.roles else None

        changed_fields = payload.model_dump(exclude_unset=True, exclude={"role_id"})
        old_values = {field: getattr(user, field) for field in changed_fields}
        for field, value in changed_fields.items():
            setattr(user, field, value)

        if changed_fields:
            # Staged alongside the field changes so a failed commit (e.g. a
            # duplicate-email constraint) rolls both back together - no audit
            # row survives for a mutation that didn't actually happen.
            await self._auth_repo.add_audit_log(
                tenant_id=tenant_id,
                user_id=actor.id,
                action="user_updated",
                entity_id=user.id,
                changes={
                    field: {"old": old_values[field], "new": value}
                    for field, value in changed_fields.items()
                },
                ip_address=ctx.ip,
                user_agent=ctx.user_agent,
                request_id=ctx.request_id,
            )
        await self._commit_or_raise()

        if new_role is not None:
            await self._repo.set_role(user.id, new_role.id, assigned_by=actor.id)
            await self._auth_repo.add_audit_log(
                tenant_id=tenant_id,
                user_id=actor.id,
                action="user_role_changed",
                entity_id=user.id,
                changes={"role": {"old": previous_role_name, "new": new_role.name}},
                ip_address=ctx.ip,
                user_agent=ctx.user_agent,
                request_id=ctx.request_id,
            )
            await self._session.commit()
            # user.roles was already loaded above (for the revocation guard),
            # so the later selectinload query in _load_response would
            # otherwise return the stale, pre-change collection instead of
            # re-querying it.
            self._session.expire(user, ["roles"])

        return await self._load_response(user_id, tenant_id)

    async def set_status(
        self,
        user_id: uuid.UUID,
        new_status: AccountStatus,
        *,
        tenant_id: uuid.UUID,
        actor: User,
        ctx: RequestContext,
    ) -> UserResponse:
        user = await self._get_or_raise(user_id, tenant_id)

        if new_status == AccountStatus.INACTIVE:
            if user.id == actor.id:
                raise CannotDeactivateSelfError("You cannot deactivate your own account")
            if self._is_administrator(user):
                remaining = await self._repo.count_other_active_admins(
                    tenant_id, exclude_user_id=user.id
                )
                if remaining == 0:
                    raise CannotDeactivateLastAdminError(
                        "Cannot deactivate the last active administrator for this tenant"
                    )

        previous_status = AccountStatus(user.status)
        user.status = new_status
        if new_status == AccountStatus.INACTIVE:
            # Deactivation must take effect immediately, not just at the next
            # access-token expiry - revoking every refresh token blocks
            # re-authentication, and get_current_user's own INACTIVE check
            # (dependencies.py) rejects the still-live access token.
            await self._auth_repo.revoke_all_for_user(user.id)
        await self._auth_repo.add_audit_log(
            tenant_id=tenant_id,
            user_id=actor.id,
            action="user_activated" if new_status == AccountStatus.ACTIVE else "user_deactivated",
            entity_id=user.id,
            changes={"status": {"old": previous_status.value, "new": new_status.value}},
            ip_address=ctx.ip,
            user_agent=ctx.user_agent,
            request_id=ctx.request_id,
        )
        await self._session.commit()

        return await self._load_response(user_id, tenant_id)

    async def list_role_options(self, *, tenant_id: uuid.UUID, actor: User) -> list[RoleSummary]:
        roles = await self._repo.list_roles(tenant_id)
        if not actor.is_superuser:
            roles = [role for role in roles if role.name != SUPER_ADMIN_ROLE]
        return [
            RoleSummary(id=role.id, name=role.name, description=role.description) for role in roles
        ]

    async def _load_response(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> UserResponse:
        user = await self._get_or_raise(user_id, tenant_id)
        return self._to_response(user)

    async def _get_or_raise(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> User:
        user = await self._repo.get_by_id(user_id, tenant_id)
        if user is None:
            raise UserNotFoundError("User not found")
        return user

    async def _get_role_or_raise(self, role_id: uuid.UUID, tenant_id: uuid.UUID) -> Role:
        role = await self._repo.get_role_by_id(role_id, tenant_id)
        if role is None:
            raise RoleNotFoundError("Role not found")
        return role

    @staticmethod
    def _guard_super_admin_assignment(role: Role, actor: User) -> None:
        if role.name == SUPER_ADMIN_ROLE and not actor.is_superuser:
            raise SuperAdminRoleProtectedError("Only a superuser can assign the super_admin role")

    @staticmethod
    def _guard_super_admin_revocation(user: User, actor: User) -> None:
        if not actor.is_superuser and any(role.name == SUPER_ADMIN_ROLE for role in user.roles):
            raise SuperAdminRoleProtectedError(
                "Only a superuser can change a super_admin user's role"
            )

    @staticmethod
    def _is_administrator(user: User) -> bool:
        return user.is_superuser or any(
            role.name in (ADMIN_ROLE, SUPER_ADMIN_ROLE) for role in user.roles
        )

    async def _commit_or_raise(self) -> None:
        """Commit, translating a unique-constraint violation into a clean 409 -
        mirrors CompanyService._commit_or_raise (check-then-insert races the
        constraint itself resolves, not a pre-check SELECT)."""
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise self._translate_integrity_error(exc) from exc

    @staticmethod
    def _translate_integrity_error(exc: IntegrityError) -> AppException:
        driver_error = getattr(exc.orig, "__cause__", None)
        constraint = getattr(driver_error, "constraint_name", None) or ""
        if constraint == "ix_users_tenant_email":
            return DuplicateUserEmailError("A user with this email already exists")
        if constraint == "ix_users_tenant_username":
            return DuplicateUsernameError("A user with this username already exists")
        return ConflictError("This operation conflicts with existing data")

    @staticmethod
    def _to_response(user: User) -> UserResponse:
        role = user.roles[0] if user.roles else None
        return UserResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            phone=user.phone,
            status=AccountStatus(user.status),
            is_superuser=user.is_superuser,
            last_login_at=user.last_login_at,
            role=RoleSummary(id=role.id, name=role.name, description=role.description)
            if role
            else None,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
