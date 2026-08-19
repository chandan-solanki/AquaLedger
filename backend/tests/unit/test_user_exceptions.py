import pytest

from app.core.errors import (
    AppException,
    AuthorizationError,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
)
from app.modules.auth.exceptions import UserNotFoundError
from app.modules.users.exceptions import (
    CannotDeactivateLastAdminError,
    CannotDeactivateSelfError,
    DuplicateUserEmailError,
    DuplicateUsernameError,
    RoleNotFoundError,
    SuperAdminRoleProtectedError,
)


@pytest.mark.parametrize(
    ("exc_cls", "expected_status", "expected_code", "expected_base"),
    [
        (UserNotFoundError, 404, "USER_NOT_FOUND", NotFoundError),
        (RoleNotFoundError, 404, "ROLE_NOT_FOUND", NotFoundError),
        (DuplicateUserEmailError, 409, "DUPLICATE_USER_EMAIL", ConflictError),
        (DuplicateUsernameError, 409, "DUPLICATE_USERNAME", ConflictError),
        (CannotDeactivateSelfError, 422, "CANNOT_DEACTIVATE_SELF", BusinessRuleError),
        (CannotDeactivateLastAdminError, 422, "CANNOT_DEACTIVATE_LAST_ADMIN", BusinessRuleError),
        (SuperAdminRoleProtectedError, 403, "SUPER_ADMIN_ROLE_PROTECTED", AuthorizationError),
    ],
)
def test_user_exception_status_and_code(
    exc_cls: type[AppException],
    expected_status: int,
    expected_code: str,
    expected_base: type[AppException],
) -> None:
    exc = exc_cls("boom")
    assert exc.status_code == expected_status
    assert exc.code == expected_code
    assert isinstance(exc, expected_base)
    assert isinstance(exc, AppException)


def test_business_rule_errors_are_distinct_from_not_found_and_conflict() -> None:
    assert not issubclass(CannotDeactivateSelfError, NotFoundError)
    assert not issubclass(CannotDeactivateSelfError, ConflictError)
    assert not issubclass(CannotDeactivateLastAdminError, NotFoundError)
    assert not issubclass(CannotDeactivateLastAdminError, ConflictError)


def test_super_admin_role_protected_is_an_authorization_error_not_a_business_rule() -> None:
    assert not issubclass(SuperAdminRoleProtectedError, BusinessRuleError)
    assert issubclass(SuperAdminRoleProtectedError, AuthorizationError)
