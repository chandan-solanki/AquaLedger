import math
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.request_context import RequestContext
from app.common.schemas import PaginatedResponse, PaginationMeta
from app.core.errors import AppException, ConflictError, InternalError, ValidationError
from app.modules.auth.constants import (
    ADMIN_ROLE,
    DEFAULT_TENANT_SLUG,
    SYSTEM_ROLES,
    AccountStatus,
    TenantStatus,
)
from app.modules.auth.models import Role, RolePermission, Tenant, User, UserRole
from app.modules.auth.repository import AuthRepository
from app.modules.auth.security import hash_password, password_policy_violations
from app.modules.platform_admin.exceptions import (
    DuplicateTenantSlugError,
    LastReachablePlatformAdminError,
    TenantAdministratorNotFoundError,
    TenantNotFoundError,
    TenantStatusUnchangedError,
)
from app.modules.platform_admin.repository import TenantRepository
from app.modules.platform_admin.schemas import (
    PlatformDashboardResponse,
    TenantAdministratorResponse,
    TenantAdministratorSummary,
    TenantCreateRequest,
    TenantListParams,
    TenantProvisioningResponse,
    TenantResponse,
)
from app.modules.users.exceptions import (
    CannotResetOwnPasswordError,
    DuplicateUserEmailError,
    DuplicateUsernameError,
)

# GET /platform/dashboard's "Recent Tenants" section - mirrors the Dashboard
# module's own top-N widgets (TopCustomerItem etc.), all of which cap at 5.
_RECENT_TENANTS_LIMIT = 5


class TenantService:
    """Platform-admin-only tenant provisioning and lifecycle management
    (Sprint 17 Session 2). Never touches ordinary business repositories -
    creating/suspending a tenant has no effect on how any tenant-scoped
    endpoint (fish, boats, invoices, ...) filters its own queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TenantRepository(session)
        self._auth_repo = AuthRepository(session)

    async def create_tenant(
        self, payload: TenantCreateRequest, *, actor: User, ctx: RequestContext
    ) -> TenantProvisioningResponse:
        violations = password_policy_violations(payload.administrator.password)
        if violations:
            raise ValidationError(
                "Password does not meet policy requirements",
                field_errors={"administrator.password": violations},
            )

        tenant = Tenant(
            name=payload.name,
            slug=payload.slug,
            plan=payload.plan,
            base_currency=payload.base_currency,
            fiscal_year_start_month=payload.fiscal_year_start_month,
            status=TenantStatus.ACTIVE,
        )
        admin_user: User | None = None
        try:
            self._repo.add_tenant(tenant)
            # Flush now (not just at the final commit) so a duplicate slug
            # surfaces here as an IntegrityError this method already knows
            # how to translate, rather than only at the very end - see
            # _commit_or_raise's docstring on why every mutation in this
            # module follows that pattern (mirrors CompanyService's own).
            await self._session.flush()

            default_tenant = await self._repo.get_tenant_by_slug(DEFAULT_TENANT_SLUG)
            if default_tenant is None:
                raise InternalError("The default tenant is missing; cannot provision system roles")
            default_roles = await self._repo.list_roles_with_permissions(default_tenant.id)
            if not default_roles:
                raise InternalError(
                    "The default tenant has no roles seeded; cannot provision system roles"
                )
            # Sprint 17 Session 3 (Phase 6): the default tenant is treated as
            # the authoritative baseline for provisioning new tenants, which
            # only stays safe if it is itself known-good. Rather than
            # silently copying whatever partial role set the default tenant
            # happens to have (e.g. someone manually deleted its "operator"
            # role), fail loudly the moment the baseline is missing a
            # system role, before any new tenant, role or user is created -
            # a corrupted default tenant must not be quietly replicated
            # into every tenant provisioned after it.
            default_role_names = {role.name for role in default_roles}
            missing_system_roles = set(SYSTEM_ROLES) - default_role_names
            if missing_system_roles:
                raise InternalError(
                    "The default tenant's role baseline is missing system role(s) "
                    f"{sorted(missing_system_roles)}; refusing to provision a new "
                    "tenant from a corrupted baseline"
                )

            admin_role_id: uuid.UUID | None = None
            for role in default_roles:
                new_role = Role(
                    tenant_id=tenant.id,
                    name=role.name,
                    description=role.description,
                    is_system=role.is_system,
                )
                self._repo.add_role(new_role)
                await self._session.flush()
                self._repo.add_role_permissions(
                    [
                        RolePermission(role_id=new_role.id, permission_id=permission.id)
                        for permission in role.permissions
                    ]
                )
                if role.name == ADMIN_ROLE:
                    admin_role_id = new_role.id

            if admin_role_id is None:
                raise InternalError(
                    "The default tenant has no 'admin' role; "
                    "cannot provision a tenant administrator"
                )

            # Both is_superuser=True AND the "admin" role (Phase 4): role
            # membership alone already covers every permission code that
            # exists today (the seeded "admin" role holds the full set,
            # identical to "super_admin" - Session 2 audit), but future
            # permission-adding migrations only ever patch the *default*
            # tenant's roles by name (a latent gap the same audit found) -
            # is_superuser is this tenant's safety net against that drift,
            # exactly mirroring how the one seeded platform account
            # (admin@fisherp.local) already carries both. is_platform_admin
            # is hardcoded False - never derived from any request field - so
            # provisioning a tenant can never manufacture a second platform
            # admin by accident.
            admin_user = User(
                tenant_id=tenant.id,
                email=payload.administrator.email,
                username=payload.administrator.username,
                password_hash=hash_password(payload.administrator.password),
                full_name=payload.administrator.full_name,
                status=AccountStatus.ACTIVE,
                is_superuser=True,
                is_platform_admin=False,
                # password_changed_at stays null on purpose, matching
                # UserService.create - forces a change on first login.
            )
            self._repo.add_user(admin_user)
            await self._session.flush()
            self._repo.add_user_role(
                UserRole(user_id=admin_user.id, role_id=admin_role_id, assigned_by=actor.id)
            )

            # Recorded against the platform admin's OWN tenant, not the new
            # tenant (see this module's docstring / Session 2 report for the
            # full rationale): every other call site in this codebase sets
            # tenant_id=actor.tenant_id, and the new tenant has no user who
            # could view a foreign-tenant audit row anyway at this point.
            await self._auth_repo.add_audit_log(
                tenant_id=actor.tenant_id,
                user_id=actor.id,
                action="tenant_created",
                entity_type="tenant",
                entity_id=tenant.id,
                changes={
                    "name": tenant.name,
                    "slug": tenant.slug,
                    "plan": tenant.plan,
                    "initial_admin_email": admin_user.email,
                    "initial_admin_username": admin_user.username,
                },
                ip_address=ctx.ip,
                user_agent=ctx.user_agent,
                request_id=ctx.request_id,
            )
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise self._translate_integrity_error(exc) from exc
        except Exception:
            await self._session.rollback()
            raise

        await self._session.refresh(tenant)
        await self._session.refresh(admin_user)
        return TenantProvisioningResponse(
            tenant=TenantResponse.model_validate(tenant),
            administrator=TenantAdministratorSummary(
                id=admin_user.id,
                email=admin_user.email,
                username=admin_user.username,
                full_name=admin_user.full_name,
            ),
        )

    async def list_tenants(self, params: TenantListParams) -> PaginatedResponse[TenantResponse]:
        tenants, total = await self._repo.list_tenants(
            q=params.q, status=params.status, page=params.page, page_size=params.page_size
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
        return PaginatedResponse(
            data=[TenantResponse.model_validate(t) for t in tenants], meta=meta
        )

    async def get_tenant(self, tenant_id: uuid.UUID) -> TenantResponse:
        tenant = await self._get_or_raise(tenant_id)
        return TenantResponse.model_validate(tenant)

    async def get_dashboard_summary(self) -> PlatformDashboardResponse:
        """GET /platform/dashboard (Sprint 17 Session 5) - real tenant
        lifecycle metadata only, reusing this same repository's counting and
        listing queries rather than any new cross-tenant aggregation."""
        counts = await self._repo.count_tenants_by_status()
        recent_tenants, _ = await self._repo.list_tenants(
            q=None, status=None, page=1, page_size=_RECENT_TENANTS_LIMIT
        )
        return PlatformDashboardResponse(
            total_tenants=sum(counts.values()),
            active_tenants=counts[TenantStatus.ACTIVE],
            suspended_tenants=counts[TenantStatus.SUSPENDED],
            inactive_tenants=counts[TenantStatus.INACTIVE],
            recent_tenants=[TenantResponse.model_validate(t) for t in recent_tenants],
        )

    async def change_status(
        self,
        tenant_id: uuid.UUID,
        new_status: TenantStatus,
        *,
        actor: User,
        ctx: RequestContext,
    ) -> TenantResponse:
        tenant = await self._get_or_raise(tenant_id)
        if tenant.status == new_status:
            raise TenantStatusUnchangedError(f"Tenant is already {new_status.value}")

        if new_status != TenantStatus.ACTIVE:
            # Phase 6's guardrail: never let a status change reach a state
            # where zero platform admins remain reachable anywhere on the
            # platform. This does NOT exempt platform admins from
            # raise_if_tenant_blocked (auth.service) - it only blocks the
            # *mutation* that would create that lockout in the first place.
            reachable = await self._repo.count_platform_admins_in_active_tenants(
                excluding_tenant_id=tenant.id
            )
            if reachable == 0:
                raise LastReachablePlatformAdminError(
                    "Cannot change this tenant's status: no platform administrator "
                    "would remain reachable on any active tenant"
                )

        previous_status = TenantStatus(tenant.status)
        tenant.status = new_status
        if new_status != TenantStatus.ACTIVE:
            await self._auth_repo.revoke_all_for_tenant(tenant.id)
        await self._auth_repo.add_audit_log(
            tenant_id=actor.tenant_id,
            user_id=actor.id,
            action="tenant_status_changed",
            entity_type="tenant",
            entity_id=tenant.id,
            changes={"status": {"old": previous_status.value, "new": new_status.value}},
            ip_address=ctx.ip,
            user_agent=ctx.user_agent,
            request_id=ctx.request_id,
        )
        await self._session.commit()
        await self._session.refresh(tenant)
        return TenantResponse.model_validate(tenant)

    async def list_administrators(self, tenant_id: uuid.UUID) -> list[TenantAdministratorResponse]:
        """Sprint 17 Session 7 - lets a platform admin identify which user
        to target for a password reset. Identity fields only, never roles/
        permissions/business data (mirrors TenantAdministratorSummary's own
        restraint at provisioning time)."""
        await self._get_or_raise(tenant_id)
        admins = await self._repo.list_administrators(tenant_id)
        return [
            TenantAdministratorResponse(
                id=admin.id,
                email=admin.email,
                username=admin.username,
                full_name=admin.full_name,
                is_superuser=admin.is_superuser,
                status=admin.status,
            )
            for admin in admins
        ]

    async def reset_administrator_password(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        new_password: str,
        *,
        actor: User,
        ctx: RequestContext,
    ) -> TenantAdministratorResponse:
        """Sprint 17 Session 7 - a platform-admin-only escape hatch for a
        locked-out tenant. Deliberately narrow: `TenantRepository.
        get_administrator` only ever returns a user who is actually an
        administrator (is_superuser or admin/super_admin role) of this
        specific tenant, so this can never be used to touch an arbitrary
        tenant user. Mirrors UserService.reset_password's own behavior
        exactly (must_change_password on next login, every existing session
        revoked) - this grants the platform admin no ongoing access to the
        tenant, and never touches is_superuser/is_platform_admin/roles."""
        await self._get_or_raise(tenant_id)
        user = await self._repo.get_administrator(tenant_id, user_id)
        if user is None:
            raise TenantAdministratorNotFoundError("Tenant administrator not found")
        if user.id == actor.id:
            raise CannotResetOwnPasswordError(
                "Use Change Password in your own profile to change your own password"
            )

        violations = password_policy_violations(new_password)
        if violations:
            raise ValidationError(
                "Password does not meet policy requirements",
                field_errors={"new_password": violations},
            )

        user.password_hash = hash_password(new_password)
        user.password_changed_at = None
        await self._auth_repo.revoke_all_for_user(user.id)
        await self._auth_repo.add_audit_log(
            tenant_id=actor.tenant_id,
            user_id=actor.id,
            action="tenant_administrator_password_reset",
            entity_type="user",
            entity_id=user.id,
            changes={"tenant_id": str(tenant_id)},
            ip_address=ctx.ip,
            user_agent=ctx.user_agent,
            request_id=ctx.request_id,
        )
        await self._session.commit()
        await self._session.refresh(user)
        return TenantAdministratorResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            is_superuser=user.is_superuser,
            status=user.status,
        )

    async def _get_or_raise(self, tenant_id: uuid.UUID) -> Tenant:
        tenant = await self._repo.get_tenant_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundError("Tenant not found")
        return tenant

    @staticmethod
    def _translate_integrity_error(exc: IntegrityError) -> AppException:
        # asyncpg's UniqueViolationError (with .constraint_name) is chained as
        # __cause__ underneath SQLAlchemy's DBAPI-compatibility wrapper (.orig) -
        # mirrors CompanyService/UserService's own _translate_integrity_error.
        driver_error = getattr(exc.orig, "__cause__", None)
        constraint = getattr(driver_error, "constraint_name", None) or ""
        if constraint == "tenants_slug_key":
            return DuplicateTenantSlugError("A tenant with this slug already exists")
        if constraint == "ix_users_tenant_email":
            return DuplicateUserEmailError("A user with this email already exists")
        if constraint == "ix_users_tenant_username":
            return DuplicateUsernameError("A user with this username already exists")
        return ConflictError("This operation conflicts with existing data")
