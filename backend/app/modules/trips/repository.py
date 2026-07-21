import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.trips.constants import TripStatus, TripType
from app.modules.trips.models import Trip

_SORT_COLUMNS: dict[str, Any] = {
    "trip_number": Trip.trip_number,
    "departure_datetime": Trip.departure_datetime,
    "created_at": Trip.created_at,
    "updated_at": Trip.updated_at,
}


class TripRepository:
    """All raw queries for the trips module live here - services never build SQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, trip_id: uuid.UUID, tenant_id: uuid.UUID) -> Trip | None:
        result = await self._session.execute(
            select(Trip).where(
                Trip.id == trip_id,
                Trip.tenant_id == tenant_id,
                Trip.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        tenant_id: uuid.UUID,
        *,
        q: str | None,
        q_boat_ids: list[uuid.UUID] | None,
        boat_id: uuid.UUID | None,
        status: TripStatus | None,
        trip_type: TripType | None,
        departure_date_from: date | None,
        departure_date_to: date | None,
        return_date_from: date | None,
        return_date_to: date | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> tuple[list[Trip], int]:
        """Filtered, sorted, paginated trip list plus the total match count.

        `q_boat_ids` is pre-resolved by the service (via BoatService) rather
        than joined here - repositories never import another module's ORM
        model directly (ARCHITECTURE.md §2). Two queries (count + page), not
        N+1. Tie-broken by id *in the same direction as the primary sort* -
        two rows created in the same instant (or with equal created_at)
        would otherwise always break ascending regardless of whether the
        caller asked for `-created_at`, silently contradicting the requested
        order.
        """
        conditions = [Trip.tenant_id == tenant_id, Trip.deleted_at.is_(None)]
        if boat_id is not None:
            conditions.append(Trip.boat_id == boat_id)
        if status is not None:
            conditions.append(Trip.status == status)
        if trip_type is not None:
            conditions.append(Trip.trip_type == trip_type)
        if departure_date_from is not None:
            conditions.append(func.date(Trip.departure_datetime) >= departure_date_from)
        if departure_date_to is not None:
            conditions.append(func.date(Trip.departure_datetime) <= departure_date_to)
        if return_date_from is not None:
            conditions.append(func.date(Trip.actual_return_datetime) >= return_date_from)
        if return_date_to is not None:
            conditions.append(func.date(Trip.actual_return_datetime) <= return_date_to)
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            q_conditions = [
                Trip.trip_number.ilike(pattern),
                Trip.captain_name.ilike(pattern),
            ]
            if q_boat_ids:
                q_conditions.append(Trip.boat_id.in_(q_boat_ids))
            conditions.append(or_(*q_conditions))

        total = (
            await self._session.execute(select(func.count()).select_from(Trip).where(*conditions))
        ).scalar_one()

        sort_field = sort[1:] if sort.startswith("-") else sort
        column = _SORT_COLUMNS[sort_field]
        descending = sort.startswith("-")
        order = column.desc() if descending else column.asc()
        tie_break = Trip.id.desc() if descending else Trip.id.asc()

        rows = (
            (
                await self._session.execute(
                    select(Trip)
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

    async def add(self, trip: Trip) -> Trip:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits (and can catch the unique-
        constraint violation) as a single, deliberate step."""
        self._session.add(trip)
        return trip
