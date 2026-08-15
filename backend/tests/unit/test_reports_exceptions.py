import pytest

from app.core.errors import AppException, NotFoundError
from app.modules.reports.exceptions import ReportCustomerNotFoundError, ReportSupplierNotFoundError


@pytest.mark.parametrize(
    ("exc_cls", "expected_status", "expected_code", "expected_base"),
    [
        (ReportCustomerNotFoundError, 404, "REPORT_CUSTOMER_NOT_FOUND", NotFoundError),
        (ReportSupplierNotFoundError, 404, "REPORT_SUPPLIER_NOT_FOUND", NotFoundError),
    ],
)
def test_report_exception_status_and_code(
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
