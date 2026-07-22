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

    async def increase_outstanding(
        self, company_id: uuid.UUID, amount: Decimal, *, tenant_id: uuid.UUID
    ) -> None:
        """Adds `amount` to the company's outstanding_amount - the Sprint 9
        Session 5 issue workflow's "Update Company outstanding_amount" step
        (ARCHITECTURE.md §13.3). The caller (InvoiceService.issue) owns the
        transaction and commits; this only stages the write, same as every
        other cross-module mutation in this codebase."""
        await self._repo.increase_outstanding_amount(company_id, tenant_id, amount)

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
