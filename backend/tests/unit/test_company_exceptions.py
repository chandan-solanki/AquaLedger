import pytest

from app.core.errors import AppException, BusinessRuleError, ConflictError, NotFoundError
from app.modules.companies.exceptions import (
    CompanyNotFoundError,
    CompanyOutstandingCalculationError,
    DuplicateCompanyCodeError,
    DuplicateCompanyNameError,
)


@pytest.mark.parametrize(
    ("exc_cls", "expected_status", "expected_code", "expected_base"),
    [
        (CompanyNotFoundError, 404, "COMPANY_NOT_FOUND", NotFoundError),
        (DuplicateCompanyCodeError, 409, "DUPLICATE_COMPANY_CODE", ConflictError),
        (DuplicateCompanyNameError, 409, "DUPLICATE_COMPANY_NAME", ConflictError),
        (
            CompanyOutstandingCalculationError,
            422,
            "COMPANY_OUTSTANDING_CALCULATION_ERROR",
            BusinessRuleError,
        ),
    ],
)
def test_company_exception_status_and_code(
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


def test_duplicate_errors_are_distinct_from_not_found() -> None:
    assert not issubclass(DuplicateCompanyCodeError, NotFoundError)
    assert not issubclass(DuplicateCompanyNameError, NotFoundError)
    assert not issubclass(CompanyNotFoundError, ConflictError)


def test_outstanding_calculation_error_is_distinct_from_not_found_and_conflict() -> None:
    assert not issubclass(CompanyOutstandingCalculationError, NotFoundError)
    assert not issubclass(CompanyOutstandingCalculationError, ConflictError)
