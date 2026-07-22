import math
import uuid
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import PaginatedResponse, PaginationMeta
from app.modules.trip_expenses.exceptions import (
    TripExpenseDateAfterReturnError,
    TripExpenseDateBeforeDepartureError,
    TripExpenseNotFoundError,
    TripExpenseTripCancelledError,
    TripExpenseTripNotFoundError,
)
from app.modules.trip_expenses.models import TripExpense
from app.modules.trip_expenses.repository import TripExpenseRepository
from app.modules.trip_expenses.schemas import (
    TripExpenseCreateRequest,
    TripExpenseListParams,
    TripExpenseResponse,
    TripExpenseUpdateRequest,
)
from app.modules.trips.constants import TripStatus
from app.modules.trips.exceptions import TripNotFoundError
from app.modules.trips.schemas import TripResponse
from app.modules.trips.service import TripService


class TripExpenseService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TripExpenseRepository(session)
        # Cross-module reference validation goes through the other module's
        # service, never its repository (ARCHITECTURE.md §2 - modules talk
        # to each other only through service.py).
        self._trip_service = TripService(session)

    async def create(
        self, payload: TripExpenseCreateRequest, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> TripExpenseResponse:
        await self._ensure_trip_valid_for_expense(payload.trip_id, payload.expense_date, tenant_id)

        trip_expense = TripExpense(
            tenant_id=tenant_id,
            trip_id=payload.trip_id,
            expense_type=payload.expense_type,
            amount=payload.amount,
            expense_date=payload.expense_date,
            description=payload.description,
            vendor_name=payload.vendor_name,
            receipt_number=payload.receipt_number,
            created_by=actor_id,
            updated_by=actor_id,
        )
        await self._repo.add(trip_expense)
        await self._session.commit()
        await self._session.refresh(trip_expense)
        return self._to_response(trip_expense)

    async def get(self, trip_expense_id: uuid.UUID, *, tenant_id: uuid.UUID) -> TripExpenseResponse:
        trip_expense = await self._get_or_raise(trip_expense_id, tenant_id)
        return self._to_response(trip_expense)

    async def list_expenses(
        self, *, tenant_id: uuid.UUID, params: TripExpenseListParams
    ) -> PaginatedResponse[TripExpenseResponse]:
        trip_expenses, total = await self._repo.search(
            tenant_id,
            q=params.q,
            trip_id=params.trip_id,
            expense_type=params.expense_type,
            expense_date_from=params.expense_date_from,
            expense_date_to=params.expense_date_to,
            sort=params.sort,
            page=params.page,
            page_size=params.page_size,
        )
        total_pages = math.ceil(total / params.page_size) if total else 0
        meta = PaginationMeta(
            total_records=total,
            total_pages=total_pages,
            current_page=params.page,
            page_size=params.page_size,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        )
        return PaginatedResponse(
            data=[self._to_response(trip_expense) for trip_expense in trip_expenses], meta=meta
        )

    async def update(
        self,
        trip_expense_id: uuid.UUID,
        payload: TripExpenseUpdateRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> TripExpenseResponse:
        trip_expense = await self._get_or_raise(trip_expense_id, tenant_id)
        update_data = payload.model_dump(exclude_unset=True)

        # Re-validate against the (possibly reassigned) trip whenever either
        # half of the trip/date pair changes - each is only meaningful
        # together with the other's current-or-new value.
        if "trip_id" in update_data or "expense_date" in update_data:
            new_trip_id = update_data.get("trip_id", trip_expense.trip_id)
            new_expense_date = update_data.get("expense_date", trip_expense.expense_date)
            await self._ensure_trip_valid_for_expense(new_trip_id, new_expense_date, tenant_id)

        for field, value in update_data.items():
            setattr(trip_expense, field, value)
        trip_expense.updated_by = actor_id
        await self._session.commit()
        await self._session.refresh(trip_expense)
        return self._to_response(trip_expense)

    async def delete(
        self, trip_expense_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        trip_expense = await self._get_or_raise(trip_expense_id, tenant_id)
        trip_expense.deleted_at = datetime.now(UTC)
        trip_expense.deleted_by = actor_id
        await self._session.commit()

    async def _ensure_trip_valid_for_expense(
        self, trip_id: uuid.UUID, expense_date: date, tenant_id: uuid.UUID
    ) -> TripResponse:
        trip = await self._get_trip_or_raise(trip_id, tenant_id)
        if trip.status == TripStatus.CANCELLED:
            raise TripExpenseTripCancelledError("Cancelled trips cannot receive new expenses")
        if expense_date < trip.departure_datetime.date():
            raise TripExpenseDateBeforeDepartureError(
                "Expense date cannot be before the trip's departure date"
            )
        if trip.actual_return_datetime is not None and (
            expense_date > trip.actual_return_datetime.date()
        ):
            raise TripExpenseDateAfterReturnError(
                "Expense date cannot be after the trip's return date"
            )
        return trip

    async def _get_trip_or_raise(self, trip_id: uuid.UUID, tenant_id: uuid.UUID) -> TripResponse:
        try:
            return await self._trip_service.get(trip_id, tenant_id=tenant_id)
        except TripNotFoundError as exc:
            raise TripExpenseTripNotFoundError("The specified trip does not exist") from exc

    async def _get_or_raise(
        self, trip_expense_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> TripExpense:
        trip_expense = await self._repo.get_by_id(trip_expense_id, tenant_id)
        if trip_expense is None:
            raise TripExpenseNotFoundError("Trip expense not found")
        return trip_expense

    @staticmethod
    def _to_response(trip_expense: TripExpense) -> TripExpenseResponse:
        return TripExpenseResponse.model_validate(trip_expense)
