import pytest

from app.core.errors import AppException, BusinessRuleError, ConflictError, NotFoundError
from app.modules.delivery_challans.exceptions import (
    DeliveryChallanEmptyError,
    DeliveryChallanInvalidTransitionError,
    DeliveryChallanInvoiceItemNotFoundError,
    DeliveryChallanInvoiceNotDeliverableError,
    DeliveryChallanInvoiceNotFoundError,
    DeliveryChallanItemNotFoundError,
    DeliveryChallanNotDraftError,
    DeliveryChallanNotFoundError,
    DeliveryChallanNumberConflictError,
    DeliveryChallanOverDeliveryError,
)


@pytest.mark.parametrize(
    ("exc_cls", "expected_status", "expected_code", "expected_base"),
    [
        (DeliveryChallanNotFoundError, 404, "DELIVERY_CHALLAN_NOT_FOUND", NotFoundError),
        (DeliveryChallanItemNotFoundError, 404, "DELIVERY_CHALLAN_ITEM_NOT_FOUND", NotFoundError),
        (
            DeliveryChallanInvoiceNotFoundError,
            404,
            "DELIVERY_CHALLAN_INVOICE_NOT_FOUND",
            NotFoundError,
        ),
        (
            DeliveryChallanInvoiceNotDeliverableError,
            422,
            "DELIVERY_CHALLAN_INVOICE_NOT_DELIVERABLE",
            BusinessRuleError,
        ),
        (
            DeliveryChallanInvoiceItemNotFoundError,
            404,
            "DELIVERY_CHALLAN_INVOICE_ITEM_NOT_FOUND",
            NotFoundError,
        ),
        (DeliveryChallanNotDraftError, 409, "DELIVERY_CHALLAN_NOT_DRAFT", ConflictError),
        (
            DeliveryChallanInvalidTransitionError,
            409,
            "DELIVERY_CHALLAN_INVALID_TRANSITION",
            ConflictError,
        ),
        (DeliveryChallanEmptyError, 422, "DELIVERY_CHALLAN_EMPTY", BusinessRuleError),
        (
            DeliveryChallanOverDeliveryError,
            422,
            "DELIVERY_CHALLAN_OVER_DELIVERY",
            BusinessRuleError,
        ),
        (
            DeliveryChallanNumberConflictError,
            409,
            "DELIVERY_CHALLAN_NUMBER_CONFLICT",
            ConflictError,
        ),
    ],
)
def test_delivery_challan_exception_status_and_code(
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
    assert not issubclass(DeliveryChallanNumberConflictError, NotFoundError)
    assert not issubclass(DeliveryChallanNotFoundError, ConflictError)


def test_not_draft_error_is_distinct_from_not_found_and_business_rule() -> None:
    assert not issubclass(DeliveryChallanNotDraftError, NotFoundError)
    assert not issubclass(DeliveryChallanNotDraftError, BusinessRuleError)


def test_invalid_transition_error_is_distinct_from_not_draft() -> None:
    """dispatch/deliver/cancel preconditions get their own exception,
    separate from the DRAFT-only mutation boundary DeliveryChallanNotDraftError
    guards."""
    assert not issubclass(DeliveryChallanInvalidTransitionError, NotFoundError)


def test_invoice_not_deliverable_error_is_distinct_from_invoice_not_found() -> None:
    assert not issubclass(DeliveryChallanInvoiceNotDeliverableError, NotFoundError)
    assert not issubclass(DeliveryChallanInvoiceNotFoundError, BusinessRuleError)


def test_over_delivery_error_is_distinct_from_invoice_item_not_found() -> None:
    assert not issubclass(DeliveryChallanOverDeliveryError, NotFoundError)
    assert not issubclass(DeliveryChallanInvoiceItemNotFoundError, BusinessRuleError)
