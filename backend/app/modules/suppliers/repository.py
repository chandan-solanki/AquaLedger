import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.suppliers.constants import SupplierStatus
from app.modules.suppliers.models import Supplier

_SORT_COLUMNS: dict[str, Any] = {
    "name": Supplier.name,
    "code": Supplier.code,
    "created_at": Supplier.created_at,
}


class SupplierRepository:
    """All raw queries for the suppliers module live here - services never
    build SQL (ARCHITECTURE.md §3.2)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, supplier_id: uuid.UUID, tenant_id: uuid.UUID) -> Supplier | None:
        result = await self._session.execute(
            select(Supplier).where(
                Supplier.id == supplier_id,
                Supplier.tenant_id == tenant_id,
                Supplier.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        tenant_id: uuid.UUID,
        *,
        q: str | None,
        status: SupplierStatus | None,
        city: str | None,
        state: str | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> tuple[list[Supplier], int]:
        """Filtered, sorted, paginated supplier list plus the total match
        count. Two queries (count + page), not N+1 - Supplier has no
        relations to eager-load. Tie-broken by id in the same direction as
        the primary sort, mirroring CompanyRepository.search /
        PaymentRepository.search."""
        conditions = [Supplier.tenant_id == tenant_id, Supplier.deleted_at.is_(None)]
        if status is not None:
            conditions.append(Supplier.status == status)
        if city and city.strip():
            conditions.append(func.lower(Supplier.city) == city.strip().lower())
        if state and state.strip():
            conditions.append(func.lower(Supplier.state) == state.strip().lower())
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            conditions.append(
                or_(
                    Supplier.name.ilike(pattern),
                    Supplier.code.ilike(pattern),
                    Supplier.gstin.ilike(pattern),
                )
            )

        total = (
            await self._session.execute(
                select(func.count()).select_from(Supplier).where(*conditions)
            )
        ).scalar_one()

        sort_field = sort[1:] if sort.startswith("-") else sort
        column = _SORT_COLUMNS[sort_field]
        descending = sort.startswith("-")
        order = column.desc() if descending else column.asc()
        tie_break = Supplier.id.desc() if descending else Supplier.id.asc()

        rows = (
            (
                await self._session.execute(
                    select(Supplier)
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

    async def add(self, supplier: Supplier) -> Supplier:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits as a single, deliberate
        step."""
        self._session.add(supplier)
        return supplier

    async def increase_outstanding_amount(
        self, supplier_id: uuid.UUID, tenant_id: uuid.UUID, amount: Decimal
    ) -> None:
        """Atomic `outstanding_amount = outstanding_amount + amount` via a
        single UPDATE expression, not a SELECT-then-write - Postgres applies
        the UPDATE atomically, so no separate row lock is needed here.
        Used by SupplierService.increase_outstanding for the Sprint 11
        Session 5 posting workflow's "Increase Supplier Outstanding" step.
        Mirrors CompanyRepository.increase_outstanding_amount exactly."""
        await self._session.execute(
            update(Supplier)
            .where(Supplier.id == supplier_id, Supplier.tenant_id == tenant_id)
            .values(outstanding_amount=Supplier.outstanding_amount + amount)
        )

    async def set_outstanding_amount(
        self, supplier_id: uuid.UUID, tenant_id: uuid.UUID, amount: Decimal
    ) -> None:
        """Overwrites outstanding_amount with an already-recomputed value -
        a straight SET, not the atomic += increase_outstanding_amount uses.
        Used by SupplierService.recalculate_outstanding for the Sprint 12
        Session 4 outstanding engine (TASKS.md: "Never increment. Always
        recompute"). Mirrors CompanyRepository.set_outstanding_amount
        exactly."""
        await self._session.execute(
            update(Supplier)
            .where(Supplier.id == supplier_id, Supplier.tenant_id == tenant_id)
            .values(outstanding_amount=amount)
        )

    async def find_ids_by_name(self, tenant_id: uuid.UUID, pattern: str) -> list[uuid.UUID]:
        """Supplier ids whose name matches `pattern` (a caller-supplied
        ILIKE pattern), for this tenant. Exists so other modules (purchase)
        can search by supplier name without importing the Supplier model
        directly - cross-module access goes through SupplierService only
        (ARCHITECTURE.md §2). Mirrors CompanyRepository.find_ids_by_name."""
        result = await self._session.execute(
            select(Supplier.id).where(
                Supplier.tenant_id == tenant_id,
                Supplier.deleted_at.is_(None),
                Supplier.name.ilike(pattern),
            )
        )
        return list(result.scalars().all())
