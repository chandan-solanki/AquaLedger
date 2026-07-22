import pytest

from app.core.errors import AppException, BusinessRuleError, ConflictError, NotFoundError
from app.modules.invoices.exceptions import (
    InvoiceCalculationError,
    InvoiceCompanyInactiveError,
    InvoiceCompanyNotFoundError,
    InvoiceEmptyError,
    InvoiceInsufficientInventoryError,
    InvoiceItemFishMismatchError,
    InvoiceItemFishNotFoundError,
    InvoiceItemNotFoundError,
    InvoiceItemQuantityExceedsAvailableError,
    InvoiceItemTripCatchNotFoundError,
    InvoiceNotDraftError,
    InvoiceNotFoundError,
    InvoiceNumberConflictError,
)


@pytest.mark.parametrize(
    ("exc_cls", "expected_status", "expected_code", "expected_base"),
    [
        (InvoiceNotFoundError, 404, "INVOICE_NOT_FOUND", NotFoundError),
        (InvoiceItemNotFoundError, 404, "INVOICE_ITEM_NOT_FOUND", NotFoundError),
        (InvoiceCompanyNotFoundError, 404, "INVOICE_COMPANY_NOT_FOUND", NotFoundError),
        (InvoiceCompanyInactiveError, 422, "INVOICE_COMPANY_INACTIVE", BusinessRuleError),
        (InvoiceNotDraftError, 409, "INVOICE_NOT_DRAFT", ConflictError),
        (
            InvoiceItemTripCatchNotFoundError,
            404,
            "INVOICE_ITEM_TRIP_CATCH_NOT_FOUND",
            NotFoundError,
        ),
        (InvoiceItemFishNotFoundError, 404, "INVOICE_ITEM_FISH_NOT_FOUND", NotFoundError),
        (
            InvoiceItemFishMismatchError,
            422,
            "INVOICE_ITEM_FISH_MISMATCH",
            BusinessRuleError,
        ),
        (
            InvoiceItemQuantityExceedsAvailableError,
            422,
            "INVOICE_ITEM_QUANTITY_EXCEEDS_AVAILABLE",
            BusinessRuleError,
        ),
        (InvoiceCalculationError, 422, "INVOICE_CALCULATION_ERROR", BusinessRuleError),
        (InvoiceEmptyError, 422, "INVOICE_EMPTY", BusinessRuleError),
        (
            InvoiceInsufficientInventoryError,
            422,
            "INVOICE_INSUFFICIENT_INVENTORY",
            BusinessRuleError,
        ),
        (InvoiceNumberConflictError, 409, "INVOICE_NUMBER_CONFLICT", ConflictError),
    ],
)
def test_invoice_exception_status_and_code(
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
        InvoiceNotFoundError,
        InvoiceItemNotFoundError,
        InvoiceCompanyNotFoundError,
        InvoiceItemTripCatchNotFoundError,
        InvoiceItemFishNotFoundError,
    )
    for exc_cls in not_found_errors:
        assert not issubclass(exc_cls, BusinessRuleError)
        assert not issubclass(exc_cls, ConflictError)


def test_business_rule_and_conflict_errors_are_not_not_found_errors() -> None:
    business_rule_and_conflict_errors = (
        InvoiceCompanyInactiveError,
        InvoiceNotDraftError,
        InvoiceItemFishMismatchError,
        InvoiceItemQuantityExceedsAvailableError,
        InvoiceCalculationError,
        InvoiceEmptyError,
        InvoiceInsufficientInventoryError,
        InvoiceNumberConflictError,
    )
    for exc_cls in business_rule_and_conflict_errors:
        assert not issubclass(exc_cls, NotFoundError)


def test_all_invoice_error_codes_are_distinct() -> None:
    codes = {
        InvoiceNotFoundError("x").code,
        InvoiceItemNotFoundError("x").code,
        InvoiceCompanyNotFoundError("x").code,
        InvoiceCompanyInactiveError("x").code,
        InvoiceNotDraftError("x").code,
        InvoiceItemTripCatchNotFoundError("x").code,
        InvoiceItemFishNotFoundError("x").code,
        InvoiceItemFishMismatchError("x").code,
        InvoiceItemQuantityExceedsAvailableError("x").code,
        InvoiceCalculationError("x").code,
        InvoiceEmptyError("x").code,
        InvoiceInsufficientInventoryError("x").code,
        InvoiceNumberConflictError("x").code,
    }
    assert len(codes) == 13
