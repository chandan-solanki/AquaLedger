from app.core.errors import BusinessRuleError, ConflictError, NotFoundError


class TenantNotFoundError(NotFoundError):
    code = "TENANT_NOT_FOUND"


class DuplicateTenantSlugError(ConflictError):
    code = "DUPLICATE_TENANT_SLUG"


class TenantStatusUnchangedError(ConflictError):
    """The requested status transition is a no-op - the tenant is already
    in that status. Rejected rather than silently accepted so a caller
    never mistakes "nothing happened" for "the change took effect"."""

    code = "TENANT_STATUS_UNCHANGED"


class TenantAdministratorNotFoundError(NotFoundError):
    """Raised for a user_id that doesn't exist in the given tenant, or
    exists but isn't actually an administrator (is_superuser or holding the
    admin/super_admin role) - a platform admin may only reset a tenant
    *administrator's* password, never an arbitrary tenant user's, so both
    cases are reported identically to avoid leaking which one it was."""

    code = "TENANT_ADMINISTRATOR_NOT_FOUND"


class LastReachablePlatformAdminError(BusinessRuleError):
    """Raised when a status change would leave zero platform administrators
    reachable anywhere on the platform (Sprint 17 Session 2 Phase 6) - every
    remaining platform admin belongs to a tenant that would no longer be
    ACTIVE. This is the narrow guardrail against a total lockout; it is not
    a blanket exemption from tenant-status enforcement (auth.service's
    raise_if_tenant_blocked still applies to platform admins with no
    exception)."""

    code = "LAST_REACHABLE_PLATFORM_ADMIN"
