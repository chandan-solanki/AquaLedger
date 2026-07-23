import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.modules.trip_expenses.exceptions import (
    TripExpenseDateAfterReturnError,
    TripExpenseDateBeforeDepartureError,
    TripExpenseTripCancelledError,
    TripExpenseTripNotFoundError,
)
from app.modules.trip_expenses.models import TripExpense
from app.modules.trip_expenses.schemas import TripExpenseListParams
from app.modules.trip_expenses.service import TripExpenseService
from app.modules.trips.constants import TripStatus
from app.modules.trips.exceptions import TripNotFoundError


class _TripStub:
    """Stands in for a TripResponse - only .status/.departure_datetime/
    .actual_return_datetime are read by TripExpenseService."""

    def __init__(
        self,
        *,
        status: TripStatus = TripStatus.PLANNED,
        departure_datetime: datetime = datetime(2026, 6, 1, 4, 0, tzinfo=UTC),
        actual_return_datetime: datetime | None = None,
    ) -> None:
        self.id = uuid.uuid4()
        self.status = status
        self.departure_datetime = departure_datetime
        self.actual_return_datetime = actual_return_datetime


class _FakeTripService:
    """Stands in for TripService.get - the only entry point TripExpenseService
    calls (ARCHITECTURE.md §2 - cross-module access goes through the other
    module's service, never its repository)."""

    def __init__(self, *, trip: _TripStub | None = None, raises: bool = False) -> None:
        self.trip = trip
        self.raises = raises
        self.get_calls: list[tuple[uuid.UUID, uuid.UUID]] = []

    async def get(self, trip_id: uuid.UUID, *, tenant_id: uuid.UUID) -> _TripStub:
        self.get_calls.append((trip_id, tenant_id))
        if self.raises:
            raise TripNotFoundError("Trip not found")
        assert self.trip is not None
        return self.trip


class _FakeTripExpenseRepo:
    def __init__(self, rows: list[TripExpense] | None = None, total: int = 0) -> None:
        self.rows = rows or []
        self.total = total
        self.last_search_call: dict[str, Any] | None = None

    async def search(self, tenant_id: uuid.UUID, **kwargs: Any) -> tuple[list[TripExpense], int]:
        self.last_search_call = {"tenant_id": tenant_id, **kwargs}
        return self.rows, self.total


def _make_trip_expense(**overrides: Any) -> TripExpense:
    """A TripExpense that satisfies TripExpenseResponse validation without
    touching the DB - the non-nullable columns normally filled by
    server_default / TimestampMixin need explicit values since this object
    is never flushed."""
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "trip_id": uuid.uuid4(),
        "expense_type": "diesel",
        "amount": Decimal("4500.00"),
        "expense_date": date(2026, 7, 22),
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return TripExpense(**defaults)


def _service_with_fakes(
    rows: list[TripExpense] | None = None,
    total: int = 0,
    *,
    trip: _TripStub | None = None,
    trip_raises: bool = False,
) -> tuple[TripExpenseService, _FakeTripExpenseRepo, _FakeTripService]:
    service = TripExpenseService.__new__(TripExpenseService)
    fake_repo = _FakeTripExpenseRepo(rows, total)
    fake_trip_service = _FakeTripService(trip=trip, raises=trip_raises)
    service._repo = fake_repo  # type: ignore[assignment]
    service._trip_service = fake_trip_service  # type: ignore[assignment]
    return service, fake_repo, fake_trip_service


class TestEnsureTripValidForExpense:
    async def test_passes_through_for_a_valid_trip_and_date(self) -> None:
        trip = _TripStub(
            status=TripStatus.PLANNED,
            departure_datetime=datetime(2026, 6, 1, 4, 0, tzinfo=UTC),
            actual_return_datetime=None,
        )
        service, _, _ = _service_with_fakes(trip=trip)

        await service._ensure_trip_valid_for_expense(trip.id, date(2026, 6, 5), uuid.uuid4())

    async def test_raises_trip_not_found_when_trip_missing(self) -> None:
        service, _, _ = _service_with_fakes(trip_raises=True)

        with pytest.raises(TripExpenseTripNotFoundError):
            await service._ensure_trip_valid_for_expense(
                uuid.uuid4(), date(2026, 6, 5), uuid.uuid4()
            )

    async def test_raises_when_trip_is_cancelled(self) -> None:
        trip = _TripStub(status=TripStatus.CANCELLED)
        service, _, _ = _service_with_fakes(trip=trip)

        with pytest.raises(TripExpenseTripCancelledError):
            await service._ensure_trip_valid_for_expense(trip.id, date(2026, 6, 5), uuid.uuid4())

    @pytest.mark.parametrize(
        "status", [TripStatus.PLANNED, TripStatus.DEPARTED, TripStatus.RETURNED]
    )
    async def test_non_cancelled_statuses_do_not_raise_the_cancelled_error(
        self, status: TripStatus
    ) -> None:
        trip = _TripStub(
            status=status,
            departure_datetime=datetime(2026, 6, 1, 4, 0, tzinfo=UTC),
            actual_return_datetime=datetime(2026, 6, 10, 4, 0, tzinfo=UTC),
        )
        service, _, _ = _service_with_fakes(trip=trip)

        await service._ensure_trip_valid_for_expense(trip.id, date(2026, 6, 5), uuid.uuid4())

    async def test_raises_when_expense_date_is_before_departure(self) -> None:
        trip = _TripStub(departure_datetime=datetime(2026, 6, 1, 4, 0, tzinfo=UTC))
        service, _, _ = _service_with_fakes(trip=trip)

        with pytest.raises(TripExpenseDateBeforeDepartureError):
            await service._ensure_trip_valid_for_expense(trip.id, date(2026, 5, 31), uuid.uuid4())

    async def test_accepts_expense_date_equal_to_departure_date(self) -> None:
        trip = _TripStub(departure_datetime=datetime(2026, 6, 1, 4, 0, tzinfo=UTC))
        service, _, _ = _service_with_fakes(trip=trip)

        await service._ensure_trip_valid_for_expense(trip.id, date(2026, 6, 1), uuid.uuid4())

    async def test_raises_when_expense_date_is_after_return(self) -> None:
        trip = _TripStub(
            departure_datetime=datetime(2026, 6, 1, 4, 0, tzinfo=UTC),
            actual_return_datetime=datetime(2026, 6, 10, 4, 0, tzinfo=UTC),
        )
        service, _, _ = _service_with_fakes(trip=trip)

        with pytest.raises(TripExpenseDateAfterReturnError):
            await service._ensure_trip_valid_for_expense(trip.id, date(2026, 6, 11), uuid.uuid4())

    async def test_accepts_expense_date_equal_to_return_date(self) -> None:
        trip = _TripStub(
            departure_datetime=datetime(2026, 6, 1, 4, 0, tzinfo=UTC),
            actual_return_datetime=datetime(2026, 6, 10, 4, 0, tzinfo=UTC),
        )
        service, _, _ = _service_with_fakes(trip=trip)

        await service._ensure_trip_valid_for_expense(trip.id, date(2026, 6, 10), uuid.uuid4())

    async def test_no_upper_bound_when_trip_has_not_returned(self) -> None:
        trip = _TripStub(
            departure_datetime=datetime(2026, 6, 1, 4, 0, tzinfo=UTC),
            actual_return_datetime=None,
        )
        service, _, _ = _service_with_fakes(trip=trip)

        await service._ensure_trip_valid_for_expense(trip.id, date(2099, 1, 1), uuid.uuid4())

    async def test_tenant_scoping_is_forwarded_to_trip_service(self) -> None:
        trip = _TripStub()
        service, _, fake_trip_service = _service_with_fakes(trip=trip)
        tenant_id = uuid.uuid4()

        await service._ensure_trip_valid_for_expense(trip.id, date(2026, 6, 5), tenant_id)

        assert fake_trip_service.get_calls == [(trip.id, tenant_id)]


class TestListExpensesPaginationMath:
    async def test_first_page_of_several(self) -> None:
        rows = [_make_trip_expense() for _ in range(2)]
        service, _, _ = _service_with_fakes(rows, total=5)

        result = await service.list_expenses(
            tenant_id=uuid.uuid4(), params=TripExpenseListParams(page=1, page_size=2)
        )

        assert len(result.data) == 2
        assert result.meta.total_records == 5
        assert result.meta.total_pages == 3
        assert result.meta.current_page == 1
        assert result.meta.has_previous is False
        assert result.meta.has_next is True

    async def test_last_page_has_no_next(self) -> None:
        rows = [_make_trip_expense()]
        service, _, _ = _service_with_fakes(rows, total=5)

        result = await service.list_expenses(
            tenant_id=uuid.uuid4(), params=TripExpenseListParams(page=3, page_size=2)
        )

        assert result.meta.has_next is False
        assert result.meta.has_previous is True

    async def test_empty_result_gives_zero_pages(self) -> None:
        service, _, _ = _service_with_fakes([], total=0)

        result = await service.list_expenses(
            tenant_id=uuid.uuid4(), params=TripExpenseListParams(page=1, page_size=20)
        )

        assert result.data == []
        assert result.meta.total_records == 0
        assert result.meta.total_pages == 0
        assert result.meta.has_next is False
        assert result.meta.has_previous is False

    async def test_filters_are_forwarded_to_the_repository(self) -> None:
        service, fake_repo, _ = _service_with_fakes([], total=0)
        tenant_id = uuid.uuid4()
        trip_id = uuid.uuid4()

        await service.list_expenses(
            tenant_id=tenant_id,
            params=TripExpenseListParams(
                q="Sassoon",
                trip_id=trip_id,
                expense_type="diesel",
                expense_date_from="2026-07-01",
                expense_date_to="2026-07-31",
                sort="-amount",
                page=2,
                page_size=10,
            ),
        )

        assert fake_repo.last_search_call is not None
        assert fake_repo.last_search_call["tenant_id"] == tenant_id
        assert fake_repo.last_search_call["q"] == "Sassoon"
        assert fake_repo.last_search_call["trip_id"] == trip_id
        assert fake_repo.last_search_call["expense_type"] == "diesel"
        assert fake_repo.last_search_call["sort"] == "-amount"
        assert fake_repo.last_search_call["page"] == 2
        assert fake_repo.last_search_call["page_size"] == 10
