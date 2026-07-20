from app.core.errors import AuthenticationError, NotFoundError


class InvalidTokenError(AuthenticationError):
    code = "INVALID_TOKEN"


class ExpiredTokenError(AuthenticationError):
    code = "EXPIRED_TOKEN"


class InvalidCredentialsError(AuthenticationError):
    """Wrong password or unknown email - message stays generic to avoid user enumeration."""

    code = "INVALID_CREDENTIALS"


class AccountLockedError(AuthenticationError):
    code = "ACCOUNT_LOCKED"


class AccountDisabledError(AuthenticationError):
    code = "ACCOUNT_DISABLED"


class UserNotFoundError(NotFoundError):
    """For future user-lookup-by-id endpoints (e.g. admin user management).

    Not the same case as an unresolvable token subject during auth, which
    stays a 401 InvalidTokenError - this is for a resource lookup that
    legitimately doesn't exist.
    """

    code = "USER_NOT_FOUND"
