import pytest

from app.core.errors import AppException, ConflictError, NotFoundError
from app.modules.boats.exceptions import (
    BoatCompanyNotFoundError,
    BoatNotFoundError,
    DuplicateBoatCodeError,
    DuplicateBoatRegistrationNumberError,
)


@pytest.mark.parametrize(
    ("exc_cls", "expected_status", "expected_code", "expected_base"),
    [
        (BoatNotFoundError, 404, "BOAT_NOT_FOUND", NotFoundError),
        (DuplicateBoatCodeError, 409, "DUPLICATE_BOAT_CODE", ConflictError),
        (
            DuplicateBoatRegistrationNumberError,
            409,
            "DUPLICATE_BOAT_REGISTRATION_NUMBER",
            ConflictError,
        ),
        (BoatCompanyNotFoundError, 404, "BOAT_COMPANY_NOT_FOUND", NotFoundError),
    ],
)
def test_boat_exception_status_and_code(
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


def test_duplicate_errors_are_not_not_found_errors() -> None:
    assert not issubclass(DuplicateBoatCodeError, NotFoundError)
    assert not issubclass(DuplicateBoatRegistrationNumberError, NotFoundError)


def test_not_found_errors_are_not_conflict_errors() -> None:
    assert not issubclass(BoatNotFoundError, ConflictError)
    assert not issubclass(BoatCompanyNotFoundError, ConflictError)


def test_boat_not_found_and_company_not_found_have_distinct_codes() -> None:
    """Both are 404 NotFoundError subclasses, but a missing boat and a
    missing referenced company are different failures the client needs to
    tell apart via error.code."""
    assert BoatNotFoundError("x").code != BoatCompanyNotFoundError("x").code
