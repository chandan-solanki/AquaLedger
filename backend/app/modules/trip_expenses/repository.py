import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.trip_expenses.constants import ExpenseType
from app.modules.trip_expenses.models import TripExpense

_SORT_COLUMNS: dict[str, Any] = {
    "expense_date": TripExpense.expense_date,
    "amount": TripExpense.amount,
    "created_at": TripExpense.created_at,
}


class TripExpenseRepository:
    """All raw queries for the trip_expenses module live here - services
    never build SQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, trip_expense_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> TripExpense | None:
        result = await self._session.execute(
            select(TripExpense).where(
                TripExpense.id == trip_expense_id,
                TripExpense.tenant_id == tenant_id,
                TripExpense.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        tenant_id: uuid.UUID,
        *,
        q: str | None,
        trip_id: uuid.UUID | None,
        expense_type: ExpenseType | None,
        expense_date_from: date | None,
        expense_date_to: date | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> tuple[list[TripExpense], int]:
        """Filtered, sorted, paginated trip expense list plus the total match
        count.

        Unlike trip_catches' search, vendor_name/receipt_number live on this
        table directly, so `q` is a plain case-insensitive substring match
        here - no cross-module id pre-resolution needed. Two queries (count +
        page), not N+1. Tie-broken by id *in the same direction as the
        primary sort* - two rows created in the same instant (or with equal
        created_at) would otherwise always break ascending regardless of
        whether the caller asked for `-created_at`, silently contradicting
        the requested order.
        """
        conditions = [TripExpense.tenant_id == tenant_id, TripExpense.deleted_at.is_(None)]
        if trip_id is not None:
            conditions.append(TripExpense.trip_id == trip_id)
        if expense_type is not None:
            conditions.append(TripExpense.expense_type == expense_type)
        if expense_date_from is not None:
            conditions.append(TripExpense.expense_date >= expense_date_from)
        if expense_date_to is not None:
            conditions.append(TripExpense.expense_date <= expense_date_to)
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            conditions.append(
                or_(
                    TripExpense.vendor_name.ilike(pattern),
                    TripExpense.receipt_number.ilike(pattern),
                )
            )

        total = (
            await self._session.execute(
                select(func.count()).select_from(TripExpense).where(*conditions)
            )
        ).scalar_one()

        sort_field = sort[1:] if sort.startswith("-") else sort
        column = _SORT_COLUMNS[sort_field]
        descending = sort.startswith("-")
        order = column.desc() if descending else column.asc()
        tie_break = TripExpense.id.desc() if descending else TripExpense.id.asc()

        rows = (
            (
                await self._session.execute(
                    select(TripExpense)
                    .where(*conditions)
                    .order_by(order, tie_break)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def add(self, trip_expense: TripExpense) -> TripExpense:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits as a single, deliberate
        step."""
        self._session.add(trip_expense)
        return trip_expense
