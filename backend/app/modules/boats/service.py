import math
import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import PaginatedResponse, PaginationMeta
from app.core.errors import AppException, ConflictError
from app.modules.boats.exceptions import (
    BoatCompanyNotFoundError,
    BoatNotFoundError,
    DuplicateBoatCodeError,
    DuplicateBoatRegistrationNumberError,
)
from app.modules.boats.models import Boat
from app.modules.boats.repository import BoatRepository
from app.modules.boats.schemas import (
    BoatCreateRequest,
    BoatListParams,
    BoatResponse,
    BoatUpdateRequest,
)
from app.modules.companies.exceptions import CompanyNotFoundError
from app.modules.companies.service import CompanyService


class BoatService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = BoatRepository(session)
        # Cross-module reference validation goes through the other module's
        # service, never its repository (ARCHITECTURE.md §2 - modules talk
        # to each other only through service.py).
        self._company_service = CompanyService(session)

    async def create(
        self, payload: BoatCreateRequest, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> BoatResponse:
        await self._ensure_company_exists(payload.company_id, tenant_id)
        boat = Boat(
            tenant_id=tenant_id,
            company_id=payload.company_id,
            code=payload.code,
            name=payload.name,
            registration_number=payload.registration_number,
            license_number=payload.license_number,
            boat_type=payload.boat_type,
            capacity_kg=payload.capacity_kg,
            engine_number=payload.engine_number,
            engine_hp=payload.engine_hp,
            captain_name=payload.captain_name,
            captain_phone=payload.captain_phone,
            insurance_expiry=payload.insurance_expiry,
            license_expiry=payload.license_expiry,
            notes=payload.notes,
            is_active=payload.is_active,
            created_by=actor_id,
            updated_by=actor_id,
        )
        await self._repo.add(boat)
        await self._commit_or_raise()
        await self._session.refresh(boat)
        return self._to_response(boat)

    async def get(self, boat_id: uuid.UUID, *, tenant_id: uuid.UUID) -> BoatResponse:
        boat = await self._get_or_raise(boat_id, tenant_id)
        return self._to_response(boat)

    async def list_boats(
        self, *, tenant_id: uuid.UUID, params: BoatListParams
    ) -> PaginatedResponse[BoatResponse]:
        boats, total = await self._repo.search(
            tenant_id,
            q=params.q,
            boat_type=params.boat_type,
            company_id=params.company_id,
            is_active=params.is_active,
            insurance_expired=params.insurance_expired,
            license_expired=params.license_expired,
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
        return PaginatedResponse(data=[self._to_response(boat) for boat in boats], meta=meta)

    async def update(
        self,
        boat_id: uuid.UUID,
        payload: BoatUpdateRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> BoatResponse:
        boat = await self._get_or_raise(boat_id, tenant_id)
        update_data = payload.model_dump(exclude_unset=True)
        if "company_id" in update_data:
            await self._ensure_company_exists(update_data["company_id"], tenant_id)
        for field, value in update_data.items():
            setattr(boat, field, value)
        boat.updated_by = actor_id
        await self._commit_or_raise()
        await self._session.refresh(boat)
        return self._to_response(boat)

    async def delete(
        self, boat_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        boat = await self._get_or_raise(boat_id, tenant_id)
        boat.deleted_at = datetime.now(UTC)
        boat.deleted_by = actor_id
        await self._session.commit()

    async def _ensure_company_exists(self, company_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        try:
            await self._company_service.get(company_id, tenant_id=tenant_id)
        except CompanyNotFoundError as exc:
            raise BoatCompanyNotFoundError("The specified company does not exist") from exc

    async def _get_or_raise(self, boat_id: uuid.UUID, tenant_id: uuid.UUID) -> Boat:
        boat = await self._repo.get_by_id(boat_id, tenant_id)
        if boat is None:
            raise BoatNotFoundError("Boat not found")
        return boat

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
        if constraint == "ix_boats_tenant_code":
            return DuplicateBoatCodeError("A boat with this code already exists")
        if constraint == "ix_boats_tenant_registration":
            return DuplicateBoatRegistrationNumberError(
                "A boat with this registration number already exists"
            )
        return ConflictError("This operation conflicts with existing data")

    @staticmethod
    def _to_response(boat: Boat) -> BoatResponse:
        return BoatResponse.model_validate(boat)
