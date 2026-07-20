import pytest

from app.core.errors import AppException, AuthenticationError, AuthorizationError, NotFoundError
from app.modules.auth.exceptions import (
    AccountDisabledError,
    AccountLockedError,
    ExpiredTokenError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserNotFoundError,
)


@pytest.mark.parametrize(
    ("exc_cls", "expected_status", "expected_code", "expected_base"),
    [
        (InvalidTokenError, 401, "INVALID_TOKEN", AuthenticationError),
        (ExpiredTokenError, 401, "EXPIRED_TOKEN", AuthenticationError),
        (InvalidCredentialsError, 401, "INVALID_CREDENTIALS", AuthenticationError),
        (AccountLockedError, 401, "ACCOUNT_LOCKED", AuthenticationError),
        (AccountDisabledError, 401, "ACCOUNT_DISABLED", AuthenticationError),
        (UserNotFoundError, 404, "USER_NOT_FOUND", NotFoundError),
    ],
)
def test_auth_exception_status_and_code(
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


def test_authorization_error_is_403_and_distinct_from_authentication() -> None:
    assert AuthorizationError("nope").status_code == 403
    assert not issubclass(AuthorizationError, AuthenticationError)
