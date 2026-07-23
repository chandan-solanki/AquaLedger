import pytest

from app.core.errors import AppException, BusinessRuleError, ConflictError, NotFoundError
from app.modules.payments.exceptions import (
    PaymentAllocationAmountExceededError,
    PaymentAllocationInvoiceInvalidStatusError,
    PaymentAllocationInvoiceNotFoundError,
    PaymentAllocationNotFoundError,
    PaymentAllocationPaymentNotDraftError,
    PaymentCompanyInactiveError,
    PaymentCompanyNotFoundError,
    PaymentNoAllocationsError,
    PaymentNotDraftError,
    PaymentNotFoundError,
    PaymentNumberConflictError,
    PaymentTotalsInvalidError,
)


@pytest.mark.parametrize(
    ("exc_cls", "expected_status", "expected_code", "expected_base"),
    [
        (PaymentNotFoundError, 404, "PAYMENT_NOT_FOUND", NotFoundError),
        (PaymentAllocationNotFoundError, 404, "PAYMENT_ALLOCATION_NOT_FOUND", NotFoundError),
        (PaymentCompanyNotFoundError, 404, "PAYMENT_COMPANY_NOT_FOUND", NotFoundError),
        (PaymentCompanyInactiveError, 422, "PAYMENT_COMPANY_INACTIVE", BusinessRuleError),
        (PaymentNotDraftError, 409, "PAYMENT_NOT_DRAFT", ConflictError),
        (
            PaymentAllocationInvoiceNotFoundError,
            404,
            "PAYMENT_ALLOCATION_INVOICE_NOT_FOUND",
            NotFoundError,
        ),
        (
            PaymentAllocationPaymentNotDraftError,
            409,
            "PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT",
            ConflictError,
        ),
        (
            PaymentAllocationInvoiceInvalidStatusError,
            422,
            "PAYMENT_ALLOCATION_INVOICE_INVALID_STATUS",
            BusinessRuleError,
        ),
        (
            PaymentAllocationAmountExceededError,
            422,
            "PAYMENT_ALLOCATION_AMOUNT_EXCEEDED",
            BusinessRuleError,
        ),
        (PaymentNoAllocationsError, 422, "PAYMENT_NO_ALLOCATIONS", BusinessRuleError),
        (PaymentTotalsInvalidError, 422, "PAYMENT_TOTALS_INVALID", BusinessRuleError),
        (PaymentNumberConflictError, 409, "PAYMENT_NUMBER_CONFLICT", ConflictError),
    ],
)
def test_payment_exception_status_and_code(
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
        PaymentNotFoundError,
        PaymentAllocationNotFoundError,
        PaymentCompanyNotFoundError,
        PaymentAllocationInvoiceNotFoundError,
    )
    for exc_cls in not_found_errors:
        assert not issubclass(exc_cls, BusinessRuleError)
        assert not issubclass(exc_cls, ConflictError)


def test_business_rule_and_conflict_errors_are_not_not_found_errors() -> None:
    business_rule_and_conflict_errors = (
        PaymentCompanyInactiveError,
        PaymentNotDraftError,
        PaymentAllocationPaymentNotDraftError,
        PaymentAllocationInvoiceInvalidStatusError,
        PaymentAllocationAmountExceededError,
        PaymentNoAllocationsError,
        PaymentTotalsInvalidError,
        PaymentNumberConflictError,
    )
    for exc_cls in business_rule_and_conflict_errors:
        assert not issubclass(exc_cls, NotFoundError)


def test_all_payment_error_codes_are_distinct() -> None:
    codes = {
        PaymentNotFoundError("x").code,
        PaymentAllocationNotFoundError("x").code,
        PaymentCompanyNotFoundError("x").code,
        PaymentCompanyInactiveError("x").code,
        PaymentNotDraftError("x").code,
        PaymentAllocationInvoiceNotFoundError("x").code,
        PaymentAllocationPaymentNotDraftError("x").code,
        PaymentAllocationInvoiceInvalidStatusError("x").code,
        PaymentAllocationAmountExceededError("x").code,
        PaymentNoAllocationsError("x").code,
        PaymentTotalsInvalidError("x").code,
        PaymentNumberConflictError("x").code,
    }
    assert len(codes) == 12
