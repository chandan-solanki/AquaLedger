import math
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import PaginatedResponse, PaginationMeta
from app.core.errors import AppException, ConflictError
from app.modules.fish.exceptions import FishNotFoundError
from app.modules.fish.service import FishService
from app.modules.trip_catches.exceptions import (
    TripCatchFishNotFoundError,
    TripCatchNotFoundError,
    TripCatchQuantityInvariantError,
    TripCatchTripNotFoundError,
    TripCatchTripNotReturnedError,
)
from app.modules.trip_catches.models import TripCatch
from app.modules.trip_catches.repository import TripCatchRepository
from app.modules.trip_catches.schemas import (
    TripCatchCreateRequest,
    TripCatchListParams,
    TripCatchResponse,
    TripCatchUpdateRequest,
)
from app.modules.trips.constants import TripStatus
from app.modules.trips.exceptions import TripNotFoundError
from app.modules.trips.service import TripService


class TripCatchService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TripCatchRepository(session)
        # Cross-module reference validation goes through the other module's
        # service, never its repository (ARCHITECTURE.md §2 - modules talk
        # to each other only through service.py).
        self._trip_service = TripService(session)
        self._fish_service = FishService(session)

    async def create(
        self, payload: TripCatchCreateRequest, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> TripCatchResponse:
        await self._ensure_trip_returned(payload.trip_id, tenant_id)
        await self._ensure_fish_exists(payload.fish_id, tenant_id)

        # available_quantity = quantity_caught, sold_quantity = waste_quantity
        # = 0 is a fixed invariant at creation time (Session 3 business
        # rule), not a client-supplied value - see TripCatchCreateRequest.
        trip_catch = TripCatch(
            tenant_id=tenant_id,
            trip_id=payload.trip_id,
            fish_id=payload.fish_id,
            grade=payload.grade,
            quantity_caught=payload.quantity_caught,
            available_quantity=payload.quantity_caught,
            sold_quantity=Decimal("0"),
            waste_quantity=Decimal("0"),
            landing_date=payload.landing_date,
            landing_port=payload.landing_port,
            remarks=payload.remarks,
            created_by=actor_id,
            updated_by=actor_id,
        )
        await self._repo.add(trip_catch)
        await self._commit_or_raise()
        await self._session.refresh(trip_catch)
        return self._to_response(trip_catch)

    async def get(self, trip_catch_id: uuid.UUID, *, tenant_id: uuid.UUID) -> TripCatchResponse:
        trip_catch = await self._get_or_raise(trip_catch_id, tenant_id)
        return self._to_response(trip_catch)

    async def list_catches(
        self, *, tenant_id: uuid.UUID, params: TripCatchListParams
    ) -> PaginatedResponse[TripCatchResponse]:
        # Trip-number/fish-name search is resolved through TripService/
        # FishService (not a repository join) - modules never import
        # another module's ORM model directly.
        q_trip_ids: list[uuid.UUID] | None = None
        q_fish_ids: list[uuid.UUID] | None = None
        if params.q and params.q.strip():
            q_trip_ids = await self._trip_service.find_ids_by_trip_number(tenant_id, params.q)
            q_fish_ids = await self._fish_service.find_ids_by_name(tenant_id, params.q)

        trip_catches, total = await self._repo.search(
            tenant_id,
            q=params.q,
            q_trip_ids=q_trip_ids,
            q_fish_ids=q_fish_ids,
            trip_id=params.trip_id,
            fish_id=params.fish_id,
            grade=params.grade,
            landing_date_from=params.landing_date_from,
            landing_date_to=params.landing_date_to,
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
            data=[self._to_response(trip_catch) for trip_catch in trip_catches], meta=meta
        )

    async def update(
        self,
        trip_catch_id: uuid.UUID,
        payload: TripCatchUpdateRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> TripCatchResponse:
        # SELECT ... FOR UPDATE, not a plain read: the quantity invariant
        # check below merges the request's fields with whatever is
        # currently in the row, so two concurrent updates to the same catch
        # (e.g. two clerks recording a sale at once) must not both read the
        # same pre-update snapshot - that's a lost update, and the second
        # writer would silently erase the first's change even though each
        # write is individually invariant-valid. Locking here serializes
        # the two requests: the second one blocks until the first commits,
        # then reads its committed values and re-validates against them
        # (naturally surfacing TripCatchQuantityInvariantError - a 409-like
        # "your view was stale" signal - if the merge no longer adds up).
        # Single-row lock by primary key, so this cannot deadlock against
        # itself the way multi-row locking (e.g. payment allocations) can.
        trip_catch = await self._get_or_raise_for_update(trip_catch_id, tenant_id)
        update_data = payload.model_dump(exclude_unset=True)

        new_trip_id = update_data.get("trip_id", trip_catch.trip_id)
        if "trip_id" in update_data and new_trip_id != trip_catch.trip_id:
            await self._ensure_trip_returned(new_trip_id, tenant_id)
        if "fish_id" in update_data:
            await self._ensure_fish_exists(update_data["fish_id"], tenant_id)

        if {"quantity_caught", "available_quantity", "sold_quantity", "waste_quantity"} & set(
            update_data
        ):
            self._ensure_quantity_invariant(
                quantity_caught=update_data.get("quantity_caught", trip_catch.quantity_caught),
                available_quantity=update_data.get(
                    "available_quantity", trip_catch.available_quantity
                ),
                sold_quantity=update_data.get("sold_quantity", trip_catch.sold_quantity),
                waste_quantity=update_data.get("waste_quantity", trip_catch.waste_quantity),
            )

        for field, value in update_data.items():
            setattr(trip_catch, field, value)
        trip_catch.updated_by = actor_id
        await self._commit_or_raise()
        await self._session.refresh(trip_catch)
        return self._to_response(trip_catch)

    async def delete(
        self, trip_catch_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        trip_catch = await self._get_or_raise(trip_catch_id, tenant_id)
        trip_catch.deleted_at = datetime.now(UTC)
        trip_catch.deleted_by = actor_id
        await self._session.commit()

    async def _ensure_trip_returned(self, trip_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        try:
            trip = await self._trip_service.get(trip_id, tenant_id=tenant_id)
        except TripNotFoundError as exc:
            raise TripCatchTripNotFoundError("The specified trip does not exist") from exc
        if trip.status != TripStatus.RETURNED:
            raise TripCatchTripNotReturnedError("The specified trip has not returned yet")

    async def _ensure_fish_exists(self, fish_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        try:
            await self._fish_service.get(fish_id, tenant_id=tenant_id)
        except FishNotFoundError as exc:
            raise TripCatchFishNotFoundError("The specified fish does not exist") from exc

    @staticmethod
    def _ensure_quantity_invariant(
        *,
        quantity_caught: Decimal,
        available_quantity: Decimal,
        sold_quantity: Decimal,
        waste_quantity: Decimal,
    ) -> None:
        if available_quantity + sold_quantity + waste_quantity != quantity_caught:
            raise TripCatchQuantityInvariantError(
                "available_quantity + sold_quantity + waste_quantity must equal quantity_caught"
            )

    async def _get_or_raise(self, trip_catch_id: uuid.UUID, tenant_id: uuid.UUID) -> TripCatch:
        trip_catch = await self._repo.get_by_id(trip_catch_id, tenant_id)
        if trip_catch is None:
            raise TripCatchNotFoundError("Trip catch not found")
        return trip_catch

    async def _get_or_raise_for_update(
        self, trip_catch_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> TripCatch:
        trip_catch = await self._repo.get_by_id_for_update(trip_catch_id, tenant_id)
        if trip_catch is None:
            raise TripCatchNotFoundError("Trip catch not found")
        return trip_catch

    async def _commit_or_raise(self) -> None:
        """Commit, translating the DB-level quantity-invariant CHECK
        constraint (ck_trip_catches_quantity_invariant, models.py) into a
        clean 422.

        The FOR UPDATE lock in update() is what actually prevents the
        invariant from being violated under concurrency; this is the
        backstop for the constraint firing regardless - a defensive catch
        that should never trigger in normal operation, same rationale as
        the boats/trips/fish services' unique-constraint translation.
        """
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise self._translate_integrity_error(exc) from exc

    @staticmethod
    def _translate_integrity_error(exc: IntegrityError) -> AppException:
        # asyncpg's CheckViolationError (with .constraint_name) is chained as
        # __cause__ underneath SQLAlchemy's DBAPI-compatibility wrapper (.orig).
        driver_error = getattr(exc.orig, "__cause__", None)
        constraint = getattr(driver_error, "constraint_name", None) or ""
        if constraint == "ck_trip_catches_quantity_invariant":
            return TripCatchQuantityInvariantError(
                "available_quantity + sold_quantity + waste_quantity must equal quantity_caught"
            )
        return ConflictError("This operation conflicts with existing data")

    @staticmethod
    def _to_response(trip_catch: TripCatch) -> TripCatchResponse:
        return TripCatchResponse.model_validate(trip_catch)
