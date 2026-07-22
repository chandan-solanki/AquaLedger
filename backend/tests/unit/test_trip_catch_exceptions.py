import pytest

from app.core.errors import AppException, BusinessRuleError, NotFoundError
from app.modules.trip_catches.exceptions import (
    TripCatchFishNotFoundError,
    TripCatchNotFoundError,
    TripCatchQuantityInvariantError,
    TripCatchTripNotFoundError,
    TripCatchTripNotReturnedError,
)


@pytest.mark.parametrize(
    ("exc_cls", "expected_status", "expected_code", "expected_base"),
    [
        (TripCatchNotFoundError, 404, "TRIP_CATCH_NOT_FOUND", NotFoundError),
        (TripCatchTripNotFoundError, 404, "TRIP_CATCH_TRIP_NOT_FOUND", NotFoundError),
        (TripCatchFishNotFoundError, 404, "TRIP_CATCH_FISH_NOT_FOUND", NotFoundError),
        (
            TripCatchTripNotReturnedError,
            422,
            "TRIP_CATCH_TRIP_NOT_RETURNED",
            BusinessRuleError,
        ),
        (
            TripCatchQuantityInvariantError,
            422,
            "TRIP_CATCH_QUANTITY_INVARIANT_VIOLATION",
            BusinessRuleError,
        ),
    ],
)
def test_trip_catch_exception_status_and_code(
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


def test_not_found_errors_are_not_business_rule_errors() -> None:
    not_found_errors = (
        TripCatchNotFoundError,
        TripCatchTripNotFoundError,
        TripCatchFishNotFoundError,
    )
    for exc_cls in not_found_errors:
        assert not issubclass(exc_cls, BusinessRuleError)


def test_business_rule_errors_are_not_not_found_errors() -> None:
    business_rule_errors = (TripCatchTripNotReturnedError, TripCatchQuantityInvariantError)
    for exc_cls in business_rule_errors:
        assert not issubclass(exc_cls, NotFoundError)


def test_trip_not_found_and_fish_not_found_have_distinct_codes() -> None:
    """Both are 404 NotFoundError subclasses, but a missing trip and a
    missing referenced fish are different failures the client needs to
    tell apart via error.code."""
    assert TripCatchTripNotFoundError("x").code != TripCatchFishNotFoundError("x").code


def test_all_trip_catch_error_codes_are_distinct() -> None:
    codes = {
        TripCatchNotFoundError("x").code,
        TripCatchTripNotFoundError("x").code,
        TripCatchFishNotFoundError("x").code,
        TripCatchTripNotReturnedError("x").code,
        TripCatchQuantityInvariantError("x").code,
    }
    assert len(codes) == 5
