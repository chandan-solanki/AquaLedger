import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.boats.models import Boat

_SORT_COLUMNS: dict[str, Any] = {
    "name": Boat.name,
    "code": Boat.code,
    "created_at": Boat.created_at,
    "updated_at": Boat.updated_at,
}


class BoatRepository:
    """All raw queries for the boats module live here - services never build SQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, boat_id: uuid.UUID, tenant_id: uuid.UUID) -> Boat | None:
        result = await self._session.execute(
            select(Boat).where(
                Boat.id == boat_id,
                Boat.tenant_id == tenant_id,
                Boat.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        tenant_id: uuid.UUID,
        *,
        q: str | None,
        boat_type: str | None,
        company_id: uuid.UUID | None,
        is_active: bool | None,
        insurance_expired: bool | None,
        license_expired: bool | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> tuple[list[Boat], int]:
        """Filtered, sorted, paginated boat list plus the total match count.

        Two queries (count + page), not N+1 - Boat has no relations to
        eager-load beyond the FK scalar. Tie-broken by id *in the same
        direction as the primary sort* - two rows created in the same
        instant (or with equal created_at) would otherwise always break
        ascending regardless of whether the caller asked for `-created_at`,
        silently contradicting the requested order.
        """
        conditions = [Boat.tenant_id == tenant_id, Boat.deleted_at.is_(None)]
        if boat_type and boat_type.strip():
            conditions.append(func.lower(Boat.boat_type) == boat_type.strip().lower())
        if company_id is not None:
            conditions.append(Boat.company_id == company_id)
        if is_active is not None:
            conditions.append(Boat.is_active == is_active)
        if insurance_expired is not None:
            conditions.append(self._expiry_condition(Boat.insurance_expiry, insurance_expired))
        if license_expired is not None:
            conditions.append(self._expiry_condition(Boat.license_expiry, license_expired))
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            conditions.append(
                or_(
                    Boat.name.ilike(pattern),
                    Boat.code.ilike(pattern),
                    Boat.registration_number.ilike(pattern),
                    Boat.captain_name.ilike(pattern),
                )
            )

        total = (
            await self._session.execute(select(func.count()).select_from(Boat).where(*conditions))
        ).scalar_one()

        sort_field = sort[1:] if sort.startswith("-") else sort
        column = _SORT_COLUMNS[sort_field]
        descending = sort.startswith("-")
        order = column.desc() if descending else column.asc()
        tie_break = Boat.id.desc() if descending else Boat.id.asc()

        rows = (
            (
                await self._session.execute(
                    select(Boat)
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

    @staticmethod
    def _expiry_condition(column: Any, expired: bool) -> Any:
        if expired:
            return (column.is_not(None)) & (column < func.current_date())
        return (column.is_(None)) | (column >= func.current_date())

    async def add(self, boat: Boat) -> Boat:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits (and can catch the unique-
        constraint violation) as a single, deliberate step."""
        self._session.add(boat)
        return boat
