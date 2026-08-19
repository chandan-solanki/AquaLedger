from app.core.errors import AuthorizationError, BusinessRuleError, ConflictError, NotFoundError

# UserNotFoundError already exists at app.modules.auth.exceptions.UserNotFoundError,
# added ahead of time for exactly this module ("future user-lookup-by-id
# endpoints (e.g. admin user management)") - reused here, not duplicated.


class RoleNotFoundError(NotFoundError):
    code = "ROLE_NOT_FOUND"


class DuplicateUserEmailError(ConflictError):
    code = "DUPLICATE_USER_EMAIL"


class DuplicateUsernameError(ConflictError):
    code = "DUPLICATE_USERNAME"


class CannotDeactivateSelfError(BusinessRuleError):
    code = "CANNOT_DEACTIVATE_SELF"


class CannotDeactivateLastAdminError(BusinessRuleError):
    code = "CANNOT_DEACTIVATE_LAST_ADMIN"


class SuperAdminRoleProtectedError(AuthorizationError):
    """Raised when a non-superuser tries to assign the super_admin role to a
    user, or change the role of a user who currently holds it - granting or
    touching that role is a privilege-escalation vector distinct from the
    user:manage permission itself (ARCHITECTURE.md's is_superuser bypass is
    a strictly stronger guarantee than holding every currently-known
    permission code, so only an existing superuser may extend it)."""

    code = "SUPER_ADMIN_ROLE_PROTECTED"
