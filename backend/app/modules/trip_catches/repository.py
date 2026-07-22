import uuid
from datetime import date
from typing import Any

from sqlalchemy import false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.trip_catches.constants import CatchGrade
from app.modules.trip_catches.models import TripCatch

_SORT_COLUMNS: dict[str, Any] = {
    "landing_date": TripCatch.landing_date,
    "quantity_caught": TripCatch.quantity_caught,
    "created_at": TripCatch.created_at,
}


class TripCatchRepository:
    """All raw queries for the trip_catches module live here - services never build SQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, trip_catch_id: uuid.UUID, tenant_id: uuid.UUID) -> TripCatch | None:
        result = await self._session.execute(
            select(TripCatch).where(
                TripCatch.id == trip_catch_id,
                TripCatch.tenant_id == tenant_id,
                TripCatch.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self, trip_catch_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> TripCatch | None:
        """Same lookup as get_by_id, but takes a row-level lock (`SELECT ...
        FOR UPDATE`) so the caller can safely read-merge-write the quantity
        columns without a concurrent update on the same row racing it - see
        TripCatchService.update()."""
        result = await self._session.execute(
            select(TripCatch)
            .where(
                TripCatch.id == trip_catch_id,
                TripCatch.tenant_id == tenant_id,
                TripCatch.deleted_at.is_(None),
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        tenant_id: uuid.UUID,
        *,
        q: str | None,
        q_trip_ids: list[uuid.UUID] | None,
        q_fish_ids: list[uuid.UUID] | None,
        trip_id: uuid.UUID | None,
        fish_id: uuid.UUID | None,
        grade: CatchGrade | None,
        landing_date_from: date | None,
        landing_date_to: date | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> tuple[list[TripCatch], int]:
        """Filtered, sorted, paginated trip catch list plus the total match
        count.

        `q_trip_ids`/`q_fish_ids` are pre-resolved by the service (via
        TripService/FishService) rather than joined here - repositories
        never import another module's ORM model directly (ARCHITECTURE.md
        §2). Unlike trips' boat-name search, trip_catches has no text column
        of its own to fall back on, so when `q` is set but both id lists are
        empty, the query must match nothing rather than everything. Two
        queries (count + page), not N+1. Tie-broken by id *in the same
        direction as the primary sort* - two rows created in the same
        instant (or with equal created_at) would otherwise always break
        ascending regardless of whether the caller asked for `-created_at`,
        silently contradicting the requested order.
        """
        conditions = [TripCatch.tenant_id == tenant_id, TripCatch.deleted_at.is_(None)]
        if trip_id is not None:
            conditions.append(TripCatch.trip_id == trip_id)
        if fish_id is not None:
            conditions.append(TripCatch.fish_id == fish_id)
        if grade is not None:
            conditions.append(TripCatch.grade == grade)
        if landing_date_from is not None:
            conditions.append(TripCatch.landing_date >= landing_date_from)
        if landing_date_to is not None:
            conditions.append(TripCatch.landing_date <= landing_date_to)
        if q and q.strip():
            id_conditions = []
            if q_trip_ids:
                id_conditions.append(TripCatch.trip_id.in_(q_trip_ids))
            if q_fish_ids:
                id_conditions.append(TripCatch.fish_id.in_(q_fish_ids))
            conditions.append(or_(*id_conditions) if id_conditions else false())

        total = (
            await self._session.execute(
                select(func.count()).select_from(TripCatch).where(*conditions)
            )
        ).scalar_one()

        sort_field = sort[1:] if sort.startswith("-") else sort
        column = _SORT_COLUMNS[sort_field]
        descending = sort.startswith("-")
        order = column.desc() if descending else column.asc()
        tie_break = TripCatch.id.desc() if descending else TripCatch.id.asc()

        rows = (
            (
                await self._session.execute(
                    select(TripCatch)
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

    async def add(self, trip_catch: TripCatch) -> TripCatch:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits as a single, deliberate
        step."""
        self._session.add(trip_catch)
        return trip_catch
