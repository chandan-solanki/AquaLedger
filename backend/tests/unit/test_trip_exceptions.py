import pytest

from app.core.errors import AppException, BusinessRuleError, ConflictError, NotFoundError
from app.modules.trips.exceptions import (
    DuplicateTripNumberError,
    TripBoatAlreadyActiveError,
    TripBoatChangeNotAllowedError,
    TripBoatNotActiveError,
    TripBoatNotFoundError,
    TripInvalidReturnDatetimeError,
    TripNotFoundError,
)


@pytest.mark.parametrize(
    ("exc_cls", "expected_status", "expected_code", "expected_base"),
    [
        (TripNotFoundError, 404, "TRIP_NOT_FOUND", NotFoundError),
        (DuplicateTripNumberError, 409, "DUPLICATE_TRIP_NUMBER", ConflictError),
        (TripBoatNotFoundError, 404, "TRIP_BOAT_NOT_FOUND", NotFoundError),
        (TripBoatNotActiveError, 422, "TRIP_BOAT_NOT_ACTIVE", BusinessRuleError),
        (TripBoatAlreadyActiveError, 422, "TRIP_BOAT_ALREADY_ACTIVE", BusinessRuleError),
        (TripInvalidReturnDatetimeError, 422, "TRIP_INVALID_RETURN_DATETIME", BusinessRuleError),
        (TripBoatChangeNotAllowedError, 409, "TRIP_BOAT_CHANGE_NOT_ALLOWED", ConflictError),
    ],
)
def test_trip_exception_status_and_code(
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


def test_duplicate_and_boat_change_errors_are_not_not_found_errors() -> None:
    assert not issubclass(DuplicateTripNumberError, NotFoundError)
    assert not issubclass(TripBoatChangeNotAllowedError, NotFoundError)


def test_not_found_errors_are_not_conflict_errors() -> None:
    assert not issubclass(TripNotFoundError, ConflictError)
    assert not issubclass(TripBoatNotFoundError, ConflictError)


def test_business_rule_errors_are_not_conflict_or_not_found_errors() -> None:
    business_rule_errors = (
        TripBoatNotActiveError,
        TripBoatAlreadyActiveError,
        TripInvalidReturnDatetimeError,
    )
    for exc_cls in business_rule_errors:
        assert not issubclass(exc_cls, ConflictError)
        assert not issubclass(exc_cls, NotFoundError)


def test_trip_not_found_and_boat_not_found_have_distinct_codes() -> None:
    """Both are 404 NotFoundError subclasses, but a missing trip and a
    missing referenced boat are different failures the client needs to
    tell apart via error.code."""
    assert TripNotFoundError("x").code != TripBoatNotFoundError("x").code


def test_all_business_rule_error_codes_are_distinct() -> None:
    codes = {
        TripBoatNotActiveError("x").code,
        TripBoatAlreadyActiveError("x").code,
        TripInvalidReturnDatetimeError("x").code,
    }
    assert len(codes) == 3
