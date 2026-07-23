import pytest

from app.core.errors import AppException, ConflictError, NotFoundError
from app.modules.suppliers.exceptions import (
    DuplicateSupplierCodeError,
    DuplicateSupplierNameError,
    SupplierNotFoundError,
)


@pytest.mark.parametrize(
    ("exc_cls", "expected_status", "expected_code", "expected_base"),
    [
        (SupplierNotFoundError, 404, "SUPPLIER_NOT_FOUND", NotFoundError),
        (DuplicateSupplierCodeError, 409, "DUPLICATE_SUPPLIER_CODE", ConflictError),
        (DuplicateSupplierNameError, 409, "DUPLICATE_SUPPLIER_NAME", ConflictError),
    ],
)
def test_supplier_exception_status_and_code(
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
    assert not issubclass(DuplicateSupplierCodeError, NotFoundError)
    assert not issubclass(DuplicateSupplierNameError, NotFoundError)
    assert not issubclass(SupplierNotFoundError, ConflictError)
