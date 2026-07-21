import pytest

from app.core.errors import AppException, ConflictError, NotFoundError
from app.modules.fish.exceptions import (
    DuplicateFishCodeError,
    DuplicateFishNameError,
    FishNotFoundError,
)


@pytest.mark.parametrize(
    ("exc_cls", "expected_status", "expected_code", "expected_base"),
    [
        (FishNotFoundError, 404, "FISH_NOT_FOUND", NotFoundError),
        (DuplicateFishCodeError, 409, "DUPLICATE_FISH_CODE", ConflictError),
        (DuplicateFishNameError, 409, "DUPLICATE_FISH_NAME", ConflictError),
    ],
)
def test_fish_exception_status_and_code(
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
    assert not issubclass(DuplicateFishCodeError, NotFoundError)
    assert not issubclass(DuplicateFishNameError, NotFoundError)
    assert not issubclass(FishNotFoundError, ConflictError)
