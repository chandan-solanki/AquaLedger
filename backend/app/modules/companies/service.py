import math
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import PaginatedResponse, PaginationMeta
from app.core.errors import AppException, ConflictError
from app.modules.companies.exceptions import (
    CompanyNotFoundError,
    CompanyOutstandingCalculationError,
    DuplicateCompanyCodeError,
    DuplicateCompanyNameError,
)
from app.modules.companies.models import Company
from app.modules.companies.repository import CompanyRepository
from app.modules.companies.schemas import (
    CompanyCreateRequest,
    CompanyListParams,
    CompanyResponse,
    CompanyUpdateRequest,
)
from app.modules.payments.domain.reconciliation import (
    ReconciliationError,
    calculate_company_outstanding,
)


class CompanyService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CompanyRepository(session)

    async def create(
        self, payload: CompanyCreateRequest, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> CompanyResponse:
        company = Company(
            tenant_id=tenant_id,
            code=payload.code,
            name=payload.name,
            legal_name=payload.legal_name,
            gstin=payload.gstin,
            pan=payload.pan,
            address_line1=payload.address_line1,
            address_line2=payload.address_line2,
            city=payload.city,
            state=payload.state,
            state_code=payload.state_code,
            pincode=payload.pincode,
            country=payload.country,
            phone=payload.phone,
            alt_phone=payload.alt_phone,
            email=payload.email,
            contact_person=payload.contact_person,
            company_type=payload.company_type,
            credit_limit=payload.credit_limit,
            credit_days=payload.credit_days,
            opening_balance=payload.opening_balance,
            opening_balance_date=payload.opening_balance_date,
            opening_balance_type=payload.opening_balance_type,
            status=payload.status,
            notes=payload.notes,
            created_by=actor_id,
            updated_by=actor_id,
        )
        await self._repo.add(company)
        await self._commit_or_raise()
        await self._session.refresh(company)
        return self._to_response(company)

    async def get(self, company_id: uuid.UUID, *, tenant_id: uuid.UUID) -> CompanyResponse:
        company = await self._get_or_raise(company_id, tenant_id)
        return self._to_response(company)

    async def list_companies(
        self, *, tenant_id: uuid.UUID, params: CompanyListParams
    ) -> PaginatedResponse[CompanyResponse]:
        companies, total = await self._repo.search(
            tenant_id,
            q=params.q,
            company_type=params.company_type,
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
            data=[self._to_response(company) for company in companies], meta=meta
        )

    async def update(
        self,
        company_id: uuid.UUID,
        payload: CompanyUpdateRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> CompanyResponse:
        company = await self._get_or_raise(company_id, tenant_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(company, field, value)
        company.updated_by = actor_id
        await self._commit_or_raise()
        await self._session.refresh(company)
        return self._to_response(company)

    async def delete(
        self, company_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        company = await self._get_or_raise(company_id, tenant_id)
        company.deleted_at = datetime.now(UTC)
        company.deleted_by = actor_id
        await self._session.commit()

    async def find_ids_by_name(self, tenant_id: uuid.UUID, q: str) -> list[uuid.UUID]:
        """Company ids whose name contains `q` (case-insensitive), for the
        invoices module's company-name search - see
        CompanyRepository.find_ids_by_name."""
        return await self._repo.find_ids_by_name(tenant_id, f"%{q.strip()}%")

    async def get_for_update(
        self, company_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> CompanyResponse | None:
        """Row-locking counterpart of get(), for recalculate_outstanding's
        caller (InvoiceService.recalculate_payment_totals) to call *before*
        summing this company's open invoice balances - the Sprint 13 Session
        3 fix for the outstanding-cache lost-update race (ARCHITECTURE.md
        §14.2). Without this lock, two concurrent recomputes for the same
        company (each triggered by a different invoice) can each read the
        SUM before either commits, then both blindly overwrite
        outstanding_amount via set_outstanding_amount - whichever commits
        last wins, silently discarding the other's contribution. Taking
        `SELECT ... FOR UPDATE` here first forces the second recompute to
        block until the first's transaction commits, so its own subsequent
        SUM read reflects the first's already-committed change.

        Acquired only *after* the payment/invoice locks the caller already
        holds (Sprint 13 Session 2, ARCHITECTURE.md §14.2's `lock payment
        FOR UPDATE; lock each target invoice FOR UPDATE`) - company is always
        the last lock taken in this chain, never the first, so this can't
        reverse an existing lock order and deadlock against it.

        Returns None rather than raising if the company is missing (e.g.
        soft-deleted while an old invoice still references it) - unlike
        get_for_update on Invoice/PurchaseBill, there is no user-facing 404
        to report here; set_outstanding_amount's own blind UPDATE already
        tolerates a non-matching row as a no-op, so this preserves that same
        tolerance instead of introducing a new failure mode for what was
        already silently accepted."""
        company = await self._repo.get_by_id_for_update(company_id, tenant_id)
        if company is None:
            return None
        return self._to_response(company)

    async def increase_outstanding(
        self, company_id: uuid.UUID, amount: Decimal, *, tenant_id: uuid.UUID
    ) -> None:
        """Adds `amount` to the company's outstanding_amount - the Sprint 9
        Session 5 issue workflow's "Update Company outstanding_amount" step
        (ARCHITECTURE.md §13.3). The caller (InvoiceService.issue) owns the
        transaction and commits; this only stages the write, same as every
        other cross-module mutation in this codebase."""
        await self._repo.increase_outstanding_amount(company_id, tenant_id, amount)

    async def recalculate_outstanding(
        self, company_id: uuid.UUID, *, tenant_id: uuid.UUID, total_open_balance: Decimal
    ) -> None:
        """Sets Company.outstanding_amount to the recomputed total - the
        Sprint 10 Session 4 outstanding engine's "Recompute, do NOT
        increment/decrement" counterpart to increase_outstanding's atomic
        +=. `total_open_balance` is the sum of balance_amount across this
        company's open invoices, computed and passed in by
        InvoiceService.recalculate_payment_totals (via its own
        InvoiceRepository - CompanyService never touches the invoices
        module's tables, ARCHITECTURE.md §2). The caller owns the
        transaction and commits; this only stages the write, same as
        increase_outstanding.
        """
        try:
            outstanding_amount = calculate_company_outstanding(
                total_open_balance=total_open_balance
            )
        except ReconciliationError as exc:
            raise CompanyOutstandingCalculationError(str(exc)) from exc
        await self._repo.set_outstanding_amount(company_id, tenant_id, outstanding_amount)

    async def _get_or_raise(self, company_id: uuid.UUID, tenant_id: uuid.UUID) -> Company:
        company = await self._repo.get_by_id(company_id, tenant_id)
        if company is None:
            raise CompanyNotFoundError("Company not found")
        return company

    async def _commit_or_raise(self) -> None:
        """Commit, translating a unique-constraint violation into a clean 409.

        Catching the DB constraint here (rather than pre-checking with a
        SELECT) avoids a check-then-insert race between concurrent requests -
        the constraint is the actual source of truth for uniqueness.
        """
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
        if constraint == "ix_companies_tenant_code":
            return DuplicateCompanyCodeError("A company with this code already exists")
        if constraint == "ix_companies_tenant_name":
            return DuplicateCompanyNameError("A company with this name already exists")
        return ConflictError("This operation conflicts with existing data")

    @staticmethod
    def _to_response(company: Company) -> CompanyResponse:
        return CompanyResponse.model_validate(company)
