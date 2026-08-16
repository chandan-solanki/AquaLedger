import pytest

from app.core.errors import AppException, BusinessRuleError, ConflictError, NotFoundError
from app.modules.purchase_orders.exceptions import (
    PurchaseOrderCalculationError,
    PurchaseOrderEmptyError,
    PurchaseOrderInvalidTransitionError,
    PurchaseOrderItemNotFoundError,
    PurchaseOrderNotDraftError,
    PurchaseOrderNotFoundError,
    PurchaseOrderNumberConflictError,
    PurchaseOrderSupplierInactiveError,
    PurchaseOrderSupplierNotFoundError,
    PurchaseOrderTotalsInvalidError,
)


@pytest.mark.parametrize(
    ("exc_cls", "expected_status", "expected_code", "expected_base"),
    [
        (PurchaseOrderNotFoundError, 404, "PURCHASE_ORDER_NOT_FOUND", NotFoundError),
        (PurchaseOrderItemNotFoundError, 404, "PURCHASE_ORDER_ITEM_NOT_FOUND", NotFoundError),
        (
            PurchaseOrderSupplierNotFoundError,
            404,
            "PURCHASE_ORDER_SUPPLIER_NOT_FOUND",
            NotFoundError,
        ),
        (
            PurchaseOrderSupplierInactiveError,
            422,
            "PURCHASE_ORDER_SUPPLIER_INACTIVE",
            BusinessRuleError,
        ),
        (PurchaseOrderNotDraftError, 409, "PURCHASE_ORDER_NOT_DRAFT", ConflictError),
        (
            PurchaseOrderInvalidTransitionError,
            409,
            "PURCHASE_ORDER_INVALID_TRANSITION",
            ConflictError,
        ),
        (PurchaseOrderCalculationError, 422, "PURCHASE_ORDER_CALCULATION_ERROR", BusinessRuleError),
        (PurchaseOrderEmptyError, 422, "PURCHASE_ORDER_EMPTY", BusinessRuleError),
        (PurchaseOrderTotalsInvalidError, 422, "PURCHASE_ORDER_TOTALS_INVALID", BusinessRuleError),
        (
            PurchaseOrderNumberConflictError,
            409,
            "PURCHASE_ORDER_NUMBER_CONFLICT",
            ConflictError,
        ),
    ],
)
def test_purchase_order_exception_status_and_code(
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
    assert not issubclass(PurchaseOrderNumberConflictError, NotFoundError)
    assert not issubclass(PurchaseOrderNotFoundError, ConflictError)


def test_not_draft_error_is_distinct_from_not_found_and_business_rule() -> None:
    assert not issubclass(PurchaseOrderNotDraftError, NotFoundError)
    assert not issubclass(PurchaseOrderNotDraftError, BusinessRuleError)


def test_invalid_transition_error_is_distinct_from_not_draft() -> None:
    """cancel/fulfill preconditions get their own exception, separate from
    the DRAFT-only mutation boundary PurchaseOrderNotDraftError guards."""
    assert not issubclass(PurchaseOrderInvalidTransitionError, NotFoundError)


def test_supplier_inactive_error_is_distinct_from_supplier_not_found() -> None:
    assert not issubclass(PurchaseOrderSupplierInactiveError, NotFoundError)
    assert not issubclass(PurchaseOrderSupplierNotFoundError, BusinessRuleError)
