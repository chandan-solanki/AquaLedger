import math
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import PaginatedResponse, PaginationMeta
from app.core.errors import AppException, ConflictError
from app.modules.suppliers.constants import SupplierStatus
from app.modules.suppliers.exceptions import (
    DuplicateSupplierCodeError,
    DuplicateSupplierNameError,
    SupplierNotFoundError,
)
from app.modules.suppliers.models import Supplier
from app.modules.suppliers.repository import SupplierRepository
from app.modules.suppliers.schemas import (
    SupplierCreateRequest,
    SupplierListParams,
    SupplierResponse,
    SupplierUpdateRequest,
)


class SupplierService:
    """Sprint 11 Session 2 - full supplier CRUD (TASKS.md), mirroring
    CompanyService's own shape closely: same search/pagination pattern,
    same soft-delete, same commit-then-translate-IntegrityError discipline
    for the (tenant_id, code) and (tenant_id, lower(name)) unique indexes.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SupplierRepository(session)

    async def create(
        self, payload: SupplierCreateRequest, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> SupplierResponse:
        supplier = Supplier(
            tenant_id=tenant_id,
            code=payload.code,
            name=payload.name,
            legal_name=payload.legal_name,
            gstin=payload.gstin,
            phone=payload.phone,
            email=payload.email,
            address=payload.address,
            city=payload.city,
            state=payload.state,
            country=payload.country,
            contact_person=payload.contact_person,
            credit_days=payload.credit_days,
            opening_balance=payload.opening_balance,
            outstanding_amount=0,
            status=SupplierStatus.ACTIVE,
            created_by=actor_id,
            updated_by=actor_id,
        )
        await self._repo.add(supplier)
        await self._commit_or_raise()
        await self._session.refresh(supplier)
        return self._to_response(supplier)

    async def get(self, supplier_id: uuid.UUID, *, tenant_id: uuid.UUID) -> SupplierResponse:
        supplier = await self._get_or_raise(supplier_id, tenant_id)
        return self._to_response(supplier)

    async def list_suppliers(
        self, *, tenant_id: uuid.UUID, params: SupplierListParams
    ) -> PaginatedResponse[SupplierResponse]:
        suppliers, total = await self._repo.search(
            tenant_id,
            q=params.q,
            status=params.status,
            city=params.city,
            state=params.state,
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
            data=[self._to_response(supplier) for supplier in suppliers], meta=meta
        )

    async def update(
        self,
        supplier_id: uuid.UUID,
        payload: SupplierUpdateRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> SupplierResponse:
        supplier = await self._get_or_raise(supplier_id, tenant_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(supplier, field, value)
        supplier.updated_by = actor_id
        await self._commit_or_raise()
        await self._session.refresh(supplier)
        return self._to_response(supplier)

    async def delete(
        self, supplier_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        supplier = await self._get_or_raise(supplier_id, tenant_id)
        supplier.deleted_at = datetime.now(UTC)
        supplier.deleted_by = actor_id
        await self._session.commit()

    async def find_ids_by_name(self, tenant_id: uuid.UUID, q: str) -> list[uuid.UUID]:
        """Supplier ids whose name contains `q` (case-insensitive), for the
        purchase module's supplier-name search - see
        SupplierRepository.find_ids_by_name."""
        return await self._repo.find_ids_by_name(tenant_id, f"%{q.strip()}%")

    async def increase_outstanding(
        self, supplier_id: uuid.UUID, amount: Decimal, *, tenant_id: uuid.UUID
    ) -> None:
        """Adds `amount` to the supplier's outstanding_amount - the Sprint
        11 Session 5 posting workflow's "Increase Supplier Outstanding" step.
        The caller (PurchaseService.post) owns the transaction and commits;
        this only stages the write, same as every other cross-module
        mutation in this codebase. Mirrors CompanyService.increase_outstanding
        exactly."""
        await self._repo.increase_outstanding_amount(supplier_id, tenant_id, amount)

    async def _get_or_raise(self, supplier_id: uuid.UUID, tenant_id: uuid.UUID) -> Supplier:
        supplier = await self._repo.get_by_id(supplier_id, tenant_id)
        if supplier is None:
            raise SupplierNotFoundError("Supplier not found")
        return supplier

    async def _commit_or_raise(self) -> None:
        """Commit, translating a unique-constraint violation into a clean
        409 - the same race-avoidance rationale CompanyService gives for
        its own unique constraints (caught here rather than pre-checked
        with a SELECT)."""
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise self._translate_integrity_error(exc) from exc

    @staticmethod
    def _translate_integrity_error(exc: IntegrityError) -> AppException:
        # asyncpg's UniqueViolationError (with .constraint_name) is chained as
        # __cause__ underneath SQLAlchemy's DBAPI-compatibility wrapper (.orig).
        driver_error = getattr(exc.orig, "__cause__", None)
        constraint = getattr(driver_error, "constraint_name", None) or ""
        if constraint == "ix_suppliers_tenant_code":
            return DuplicateSupplierCodeError("A supplier with this code already exists")
        if constraint == "ix_suppliers_tenant_name":
            return DuplicateSupplierNameError("A supplier with this name already exists")
        return ConflictError("This operation conflicts with existing data")

    @staticmethod
    def _to_response(supplier: Supplier) -> SupplierResponse:
        return SupplierResponse.model_validate(supplier)
