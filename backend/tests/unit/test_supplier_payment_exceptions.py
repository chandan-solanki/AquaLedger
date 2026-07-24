import pytest

from app.core.errors import AppException, BusinessRuleError, ConflictError, NotFoundError
from app.modules.supplier_payments.exceptions import (
    SupplierPaymentAllocationNotFoundError,
    SupplierPaymentNotDraftError,
    SupplierPaymentNotFoundError,
    SupplierPaymentSupplierInactiveError,
    SupplierPaymentSupplierNotFoundError,
)


@pytest.mark.parametrize(
    ("exc_cls", "expected_status", "expected_code", "expected_base"),
    [
        (SupplierPaymentNotFoundError, 404, "SUPPLIER_PAYMENT_NOT_FOUND", NotFoundError),
        (
            SupplierPaymentAllocationNotFoundError,
            404,
            "SUPPLIER_PAYMENT_ALLOCATION_NOT_FOUND",
            NotFoundError,
        ),
        (
            SupplierPaymentSupplierNotFoundError,
            404,
            "SUPPLIER_PAYMENT_SUPPLIER_NOT_FOUND",
            NotFoundError,
        ),
        (
            SupplierPaymentSupplierInactiveError,
            422,
            "SUPPLIER_PAYMENT_SUPPLIER_INACTIVE",
            BusinessRuleError,
        ),
        (SupplierPaymentNotDraftError, 409, "SUPPLIER_PAYMENT_NOT_DRAFT", ConflictError),
    ],
)
def test_supplier_payment_exception_status_and_code(
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
        SupplierPaymentNotFoundError,
        SupplierPaymentAllocationNotFoundError,
        SupplierPaymentSupplierNotFoundError,
    )
    for exc_cls in not_found_errors:
        assert not issubclass(exc_cls, BusinessRuleError)
        assert not issubclass(exc_cls, ConflictError)


def test_business_rule_and_conflict_errors_are_not_not_found_errors() -> None:
    business_rule_and_conflict_errors = (
        SupplierPaymentSupplierInactiveError,
        SupplierPaymentNotDraftError,
    )
    for exc_cls in business_rule_and_conflict_errors:
        assert not issubclass(exc_cls, NotFoundError)


def test_all_supplier_payment_error_codes_are_distinct() -> None:
    codes = {
        SupplierPaymentNotFoundError("x").code,
        SupplierPaymentAllocationNotFoundError("x").code,
        SupplierPaymentSupplierNotFoundError("x").code,
        SupplierPaymentSupplierInactiveError("x").code,
        SupplierPaymentNotDraftError("x").code,
    }
    assert len(codes) == 5
