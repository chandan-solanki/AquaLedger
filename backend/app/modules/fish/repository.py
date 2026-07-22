import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.fish.constants import FishUnit
from app.modules.fish.models import Fish

_SORT_COLUMNS: dict[str, Any] = {
    "name": Fish.name,
    "code": Fish.code,
    "created_at": Fish.created_at,
    "updated_at": Fish.updated_at,
}


class FishRepository:
    """All raw queries for the fish module live here - services never build SQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, fish_id: uuid.UUID, tenant_id: uuid.UUID) -> Fish | None:
        result = await self._session.execute(
            select(Fish).where(
                Fish.id == fish_id,
                Fish.tenant_id == tenant_id,
                Fish.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        tenant_id: uuid.UUID,
        *,
        q: str | None,
        category: str | None,
        unit: FishUnit | None,
        is_active: bool | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> tuple[list[Fish], int]:
        """Filtered, sorted, paginated fish list plus the total match count.

        Two queries (count + page), not N+1 - Fish has no relations to
        eager-load. Tie-broken by id *in the same direction as the primary
        sort* - two rows created in the same instant (or with equal
        created_at) would otherwise always break ascending regardless of
        whether the caller asked for `-created_at`, silently contradicting
        the requested order.
        """
        conditions = [Fish.tenant_id == tenant_id, Fish.deleted_at.is_(None)]
        if category and category.strip():
            conditions.append(func.lower(Fish.category) == category.strip().lower())
        if unit is not None:
            conditions.append(Fish.unit == unit)
        if is_active is not None:
            conditions.append(Fish.is_active == is_active)
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            conditions.append(
                or_(
                    Fish.code.ilike(pattern),
                    Fish.name.ilike(pattern),
                    Fish.local_name.ilike(pattern),
                    Fish.scientific_name.ilike(pattern),
                )
            )

        total = (
            await self._session.execute(select(func.count()).select_from(Fish).where(*conditions))
        ).scalar_one()

        sort_field = sort[1:] if sort.startswith("-") else sort
        column = _SORT_COLUMNS[sort_field]
        descending = sort.startswith("-")
        order = column.desc() if descending else column.asc()
        tie_break = Fish.id.desc() if descending else Fish.id.asc()

        rows = (
            (
                await self._session.execute(
                    select(Fish)
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

    async def add(self, fish: Fish) -> Fish:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits (and can catch the unique-
        constraint violation) as a single, deliberate step."""
        self._session.add(fish)
        return fish

    async def find_ids_by_name(self, tenant_id: uuid.UUID, pattern: str) -> list[uuid.UUID]:
        """Fish ids whose name matches `pattern` (a caller-supplied ILIKE
        pattern), for this tenant. Exists so other modules (trip_catches) can
        search by fish name without importing the Fish model directly -
        cross-module access goes through FishService only (ARCHITECTURE.md §2)."""
        result = await self._session.execute(
            select(Fish.id).where(
                Fish.tenant_id == tenant_id,
                Fish.deleted_at.is_(None),
                Fish.name.ilike(pattern),
            )
        )
        return list(result.scalars().all())
