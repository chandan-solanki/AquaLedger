import pytest

from app.core.errors import AppException, BusinessRuleError, ConflictError, NotFoundError
from app.modules.purchase.exceptions import (
    PurchaseBillEmptyError,
    PurchaseBillItemNotFoundError,
    PurchaseBillNotDraftError,
    PurchaseBillNotFoundError,
    PurchaseBillSupplierInactiveError,
    PurchaseBillSupplierNotFoundError,
    PurchaseCalculationError,
    PurchaseNumberConflictError,
    PurchaseTotalsInvalidError,
)


@pytest.mark.parametrize(
    ("exc_cls", "expected_status", "expected_code", "expected_base"),
    [
        (PurchaseBillNotFoundError, 404, "PURCHASE_BILL_NOT_FOUND", NotFoundError),
        (PurchaseBillItemNotFoundError, 404, "PURCHASE_BILL_ITEM_NOT_FOUND", NotFoundError),
        (
            PurchaseBillSupplierNotFoundError,
            404,
            "PURCHASE_BILL_SUPPLIER_NOT_FOUND",
            NotFoundError,
        ),
        (
            PurchaseBillSupplierInactiveError,
            422,
            "PURCHASE_BILL_SUPPLIER_INACTIVE",
            BusinessRuleError,
        ),
        (PurchaseBillNotDraftError, 409, "PURCHASE_BILL_NOT_DRAFT", ConflictError),
        (PurchaseCalculationError, 422, "PURCHASE_CALCULATION_ERROR", BusinessRuleError),
        (PurchaseBillEmptyError, 422, "PURCHASE_BILL_EMPTY", BusinessRuleError),
        (PurchaseTotalsInvalidError, 422, "PURCHASE_TOTALS_INVALID", BusinessRuleError),
        (
            PurchaseNumberConflictError,
            409,
            "PURCHASE_NUMBER_CONFLICT",
            ConflictError,
        ),
    ],
)
def test_purchase_exception_status_and_code(
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


def test_number_conflict_error_is_distinct_from_not_found() -> None:
    assert not issubclass(PurchaseNumberConflictError, NotFoundError)
    assert not issubclass(PurchaseBillNotFoundError, ConflictError)


def test_not_draft_error_is_distinct_from_not_found_and_business_rule() -> None:
    assert not issubclass(PurchaseBillNotDraftError, NotFoundError)
    assert not issubclass(PurchaseBillNotDraftError, BusinessRuleError)


def test_supplier_inactive_error_is_distinct_from_supplier_not_found() -> None:
    assert not issubclass(PurchaseBillSupplierInactiveError, NotFoundError)
    assert not issubclass(PurchaseBillSupplierNotFoundError, BusinessRuleError)
