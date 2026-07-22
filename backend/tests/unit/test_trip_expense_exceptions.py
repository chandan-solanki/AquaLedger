import pytest

from app.core.errors import AppException, BusinessRuleError, NotFoundError
from app.modules.trip_expenses.exceptions import (
    TripExpenseDateAfterReturnError,
    TripExpenseDateBeforeDepartureError,
    TripExpenseNotFoundError,
    TripExpenseTripCancelledError,
    TripExpenseTripNotFoundError,
)


@pytest.mark.parametrize(
    ("exc_cls", "expected_status", "expected_code", "expected_base"),
    [
        (TripExpenseNotFoundError, 404, "TRIP_EXPENSE_NOT_FOUND", NotFoundError),
        (TripExpenseTripNotFoundError, 404, "TRIP_EXPENSE_TRIP_NOT_FOUND", NotFoundError),
        (
            TripExpenseTripCancelledError,
            422,
            "TRIP_EXPENSE_TRIP_CANCELLED",
            BusinessRuleError,
        ),
        (
            TripExpenseDateBeforeDepartureError,
            422,
            "TRIP_EXPENSE_DATE_BEFORE_DEPARTURE",
            BusinessRuleError,
        ),
        (
            TripExpenseDateAfterReturnError,
            422,
            "TRIP_EXPENSE_DATE_AFTER_RETURN",
            BusinessRuleError,
        ),
    ],
)
def test_trip_expense_exception_status_and_code(
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
    not_found_errors = (TripExpenseNotFoundError, TripExpenseTripNotFoundError)
    for exc_cls in not_found_errors:
        assert not issubclass(exc_cls, BusinessRuleError)


def test_business_rule_errors_are_not_not_found_errors() -> None:
    business_rule_errors = (
        TripExpenseTripCancelledError,
        TripExpenseDateBeforeDepartureError,
        TripExpenseDateAfterReturnError,
    )
    for exc_cls in business_rule_errors:
        assert not issubclass(exc_cls, NotFoundError)


def test_all_trip_expense_error_codes_are_distinct() -> None:
    codes = {
        TripExpenseNotFoundError("x").code,
        TripExpenseTripNotFoundError("x").code,
        TripExpenseTripCancelledError("x").code,
        TripExpenseDateBeforeDepartureError("x").code,
        TripExpenseDateAfterReturnError("x").code,
    }
    assert len(codes) == 5
