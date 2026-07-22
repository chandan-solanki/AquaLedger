import math
import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import PaginatedResponse, PaginationMeta
from app.core.errors import AppException, ConflictError
from app.modules.fish.exceptions import (
    DuplicateFishCodeError,
    DuplicateFishNameError,
    FishNotFoundError,
)
from app.modules.fish.models import Fish
from app.modules.fish.repository import FishRepository
from app.modules.fish.schemas import (
    FishCreateRequest,
    FishListParams,
    FishResponse,
    FishUpdateRequest,
)


class FishService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = FishRepository(session)

    async def create(
        self, payload: FishCreateRequest, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> FishResponse:
        fish = Fish(
            tenant_id=tenant_id,
            code=payload.code,
            name=payload.name,
            local_name=payload.local_name,
            scientific_name=payload.scientific_name,
            category=payload.category,
            unit=payload.unit,
            default_purchase_rate=payload.default_purchase_rate,
            default_sale_rate=payload.default_sale_rate,
            hsn_code=payload.hsn_code,
            description=payload.description,
            is_active=payload.is_active,
            created_by=actor_id,
            updated_by=actor_id,
        )
        await self._repo.add(fish)
        await self._commit_or_raise()
        await self._session.refresh(fish)
        return self._to_response(fish)

    async def get(self, fish_id: uuid.UUID, *, tenant_id: uuid.UUID) -> FishResponse:
        fish = await self._get_or_raise(fish_id, tenant_id)
        return self._to_response(fish)

    async def list_fish(
        self, *, tenant_id: uuid.UUID, params: FishListParams
    ) -> PaginatedResponse[FishResponse]:
        fish_rows, total = await self._repo.search(
            tenant_id,
            q=params.q,
            category=params.category,
            unit=params.unit,
            is_active=params.is_active,
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
        return PaginatedResponse(data=[self._to_response(fish) for fish in fish_rows], meta=meta)

    async def update(
        self,
        fish_id: uuid.UUID,
        payload: FishUpdateRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> FishResponse:
        fish = await self._get_or_raise(fish_id, tenant_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(fish, field, value)
        fish.updated_by = actor_id
        await self._commit_or_raise()
        await self._session.refresh(fish)
        return self._to_response(fish)

    async def delete(
        self, fish_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        fish = await self._get_or_raise(fish_id, tenant_id)
        fish.deleted_at = datetime.now(UTC)
        fish.deleted_by = actor_id
        await self._session.commit()

    async def find_ids_by_name(self, tenant_id: uuid.UUID, q: str) -> list[uuid.UUID]:
        """Fish ids whose name contains `q` (case-insensitive), for the
        trip_catches module's fish-name search - see FishRepository.find_ids_by_name."""
        return await self._repo.find_ids_by_name(tenant_id, f"%{q.strip()}%")

    async def _get_or_raise(self, fish_id: uuid.UUID, tenant_id: uuid.UUID) -> Fish:
        fish = await self._repo.get_by_id(fish_id, tenant_id)
        if fish is None:
            raise FishNotFoundError("Fish not found")
        return fish

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
        if constraint == "ix_fish_tenant_code":
            return DuplicateFishCodeError("A fish with this code already exists")
        if constraint == "ix_fish_tenant_name":
            return DuplicateFishNameError("A fish with this name already exists")
        return ConflictError("This operation conflicts with existing data")

    @staticmethod
    def _to_response(fish: Fish) -> FishResponse:
        return FishResponse.model_validate(fish)
