import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.companies.constants import CompanyStatus, CompanyType
from app.modules.companies.models import Company

_SORT_COLUMNS: dict[str, Any] = {
    "name": Company.name,
    "code": Company.code,
    "created_at": Company.created_at,
    "updated_at": Company.updated_at,
}


class CompanyRepository:
    """All raw queries for the companies module live here - services never build SQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, company_id: uuid.UUID, tenant_id: uuid.UUID) -> Company | None:
        result = await self._session.execute(
            select(Company).where(
                Company.id == company_id,
                Company.tenant_id == tenant_id,
                Company.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        tenant_id: uuid.UUID,
        *,
        q: str | None,
        company_type: CompanyType | None,
        status: CompanyStatus | None,
        city: str | None,
        state: str | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> tuple[list[Company], int]:
        """Filtered, sorted, paginated company list plus the total match count.

        Two queries (count + page), not N+1 - Company has no relations to
        eager-load. Tie-broken by id so pages stay stable when the sort
        column has duplicate values across rows.
        """
        conditions = [Company.tenant_id == tenant_id, Company.deleted_at.is_(None)]
        if company_type is not None:
            conditions.append(Company.company_type == company_type)
        if status is not None:
            conditions.append(Company.status == status)
        if city and city.strip():
            conditions.append(func.lower(Company.city) == city.strip().lower())
        if state and state.strip():
            conditions.append(func.lower(Company.state) == state.strip().lower())
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            conditions.append(
                or_(
                    Company.name.ilike(pattern),
                    Company.code.ilike(pattern),
                    Company.contact_person.ilike(pattern),
                    Company.phone.ilike(pattern),
                    Company.email.ilike(pattern),
                    Company.gstin.ilike(pattern),
                )
            )

        total = (
            await self._session.execute(
                select(func.count()).select_from(Company).where(*conditions)
            )
        ).scalar_one()

        sort_field = sort[1:] if sort.startswith("-") else sort
        column = _SORT_COLUMNS[sort_field]
        order = column.desc() if sort.startswith("-") else column.asc()

        rows = (
            (
                await self._session.execute(
                    select(Company)
                    .where(*conditions)
                    .order_by(order, Company.id)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def add(self, company: Company) -> Company:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits (and can catch the unique-
        constraint violation) as a single, deliberate step."""
        self._session.add(company)
        return company

    async def increase_outstanding_amount(
        self, company_id: uuid.UUID, tenant_id: uuid.UUID, amount: Decimal
    ) -> None:
        """Atomic `outstanding_amount = outstanding_amount + amount` via a
        single UPDATE expression, not a SELECT-then-write - Postgres applies
        the UPDATE atomically, so no separate row lock is needed here
        (unlike TripCatch's available_quantity deduction, there's no prior
        business-rule check that requires reading a committed value first).
        Used by CompanyService.increase_outstanding for the Sprint 9 Session
        5 issue workflow (ARCHITECTURE.md §13.3)."""
        await self._session.execute(
            update(Company)
            .where(Company.id == company_id, Company.tenant_id == tenant_id)
            .values(outstanding_amount=Company.outstanding_amount + amount)
        )

    async def find_ids_by_name(self, tenant_id: uuid.UUID, pattern: str) -> list[uuid.UUID]:
        """Company ids whose name matches `pattern` (a caller-supplied ILIKE
        pattern), for this tenant. Exists so other modules (invoices) can
        search by company name without importing the Company model directly -
        cross-module access goes through CompanyService only (ARCHITECTURE.md §2)."""
        result = await self._session.execute(
            select(Company.id).where(
                Company.tenant_id == tenant_id,
                Company.deleted_at.is_(None),
                Company.name.ilike(pattern),
            )
        )
        return list(result.scalars().all())
