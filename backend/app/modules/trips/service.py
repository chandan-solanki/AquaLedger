import math
import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import PaginatedResponse, PaginationMeta
from app.core.errors import AppException, ConflictError
from app.modules.boats.exceptions import BoatNotFoundError
from app.modules.boats.schemas import BoatResponse
from app.modules.boats.service import BoatService
from app.modules.trips.constants import TripStatus
from app.modules.trips.exceptions import (
    DuplicateTripNumberError,
    TripBoatAlreadyActiveError,
    TripBoatChangeNotAllowedError,
    TripBoatNotActiveError,
    TripBoatNotFoundError,
    TripInvalidReturnDatetimeError,
    TripNotFoundError,
)
from app.modules.trips.models import Trip
from app.modules.trips.repository import TripRepository
from app.modules.trips.schemas import (
    TripCreateRequest,
    TripListParams,
    TripResponse,
    TripUpdateRequest,
)


class TripService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TripRepository(session)
        # Cross-module reference validation goes through the other module's
        # service, never its repository (ARCHITECTURE.md §2 - modules talk
        # to each other only through service.py).
        self._boat_service = BoatService(session)

    async def create(
        self, payload: TripCreateRequest, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> TripResponse:
        await self._get_active_boat_or_raise(payload.boat_id, tenant_id)
        self._ensure_return_after_departure(
            payload.departure_datetime, payload.actual_return_datetime
        )
        # "Boat cannot have more than one active trip" is enforced by the
        # ix_trips_boat_single_active partial unique index, not a pre-check
        # here - see _translate_integrity_error and the index's comment in
        # models.py for why (avoids a check-then-insert race).

        trip = Trip(
            tenant_id=tenant_id,
            boat_id=payload.boat_id,
            trip_number=payload.trip_number,
            trip_type=payload.trip_type,
            captain_name=payload.captain_name,
            departure_port=payload.departure_port,
            arrival_port=payload.arrival_port,
            departure_datetime=payload.departure_datetime,
            expected_return_datetime=payload.expected_return_datetime,
            actual_return_datetime=payload.actual_return_datetime,
            status=payload.status,
            notes=payload.notes,
            is_active=payload.is_active,
            created_by=actor_id,
            updated_by=actor_id,
        )
        await self._repo.add(trip)
        await self._commit_or_raise()
        await self._session.refresh(trip)
        return self._to_response(trip)

    async def get(self, trip_id: uuid.UUID, *, tenant_id: uuid.UUID) -> TripResponse:
        trip = await self._get_or_raise(trip_id, tenant_id)
        return self._to_response(trip)

    async def list_trips(
        self, *, tenant_id: uuid.UUID, params: TripListParams
    ) -> PaginatedResponse[TripResponse]:
        # Boat-name search is resolved through BoatService (not a repository
        # join) - modules never import another module's ORM model directly.
        q_boat_ids: list[uuid.UUID] | None = None
        if params.q and params.q.strip():
            q_boat_ids = await self._boat_service.find_ids_by_name(tenant_id, params.q)

        trips, total = await self._repo.search(
            tenant_id,
            q=params.q,
            q_boat_ids=q_boat_ids,
            boat_id=params.boat_id,
            status=params.status,
            trip_type=params.trip_type,
            departure_date_from=params.departure_date_from,
            departure_date_to=params.departure_date_to,
            return_date_from=params.return_date_from,
            return_date_to=params.return_date_to,
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
        return PaginatedResponse(data=[self._to_response(trip) for trip in trips], meta=meta)

    async def update(
        self,
        trip_id: uuid.UUID,
        payload: TripUpdateRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> TripResponse:
        trip = await self._get_or_raise(trip_id, tenant_id)
        update_data = payload.model_dump(exclude_unset=True)

        new_boat_id = update_data.get("boat_id", trip.boat_id)
        if "boat_id" in update_data and new_boat_id != trip.boat_id:
            if trip.status == TripStatus.RETURNED:
                raise TripBoatChangeNotAllowedError("Returned trips cannot change boat")
            await self._get_active_boat_or_raise(new_boat_id, tenant_id)
        # "Boat cannot have more than one active trip" is enforced by the
        # ix_trips_boat_single_active partial unique index (see create()).
        # Postgres checks it against the row's *new* values on UPDATE too,
        # so reassigning boat_id or flipping status back to planned/departed
        # is covered without an explicit exclude-self check here.

        if "departure_datetime" in update_data or "actual_return_datetime" in update_data:
            new_departure = update_data.get("departure_datetime", trip.departure_datetime)
            new_actual_return = update_data.get(
                "actual_return_datetime", trip.actual_return_datetime
            )
            self._ensure_return_after_departure(new_departure, new_actual_return)

        for field, value in update_data.items():
            setattr(trip, field, value)
        trip.updated_by = actor_id
        await self._commit_or_raise()
        await self._session.refresh(trip)
        return self._to_response(trip)

    async def delete(
        self, trip_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        trip = await self._get_or_raise(trip_id, tenant_id)
        trip.deleted_at = datetime.now(UTC)
        trip.deleted_by = actor_id
        await self._session.commit()

    async def find_ids_by_trip_number(self, tenant_id: uuid.UUID, q: str) -> list[uuid.UUID]:
        """Trip ids whose trip_number contains `q` (case-insensitive), for
        the trip_catches module's trip-number search - see
        TripRepository.find_ids_by_trip_number."""
        return await self._repo.find_ids_by_trip_number(tenant_id, f"%{q.strip()}%")

    async def _get_active_boat_or_raise(
        self, boat_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> BoatResponse:
        # BoatService.get() is already tenant-scoped, so a boat belonging to
        # another tenant surfaces as "not found" here too - that's the
        # correct behaviour for the "boat must belong to current tenant" rule.
        try:
            boat = await self._boat_service.get(boat_id, tenant_id=tenant_id)
        except BoatNotFoundError as exc:
            raise TripBoatNotFoundError("The specified boat does not exist") from exc
        if not boat.is_active:
            raise TripBoatNotActiveError("The specified boat is not active")
        return boat

    @staticmethod
    def _ensure_return_after_departure(
        departure_datetime: datetime, actual_return_datetime: datetime | None
    ) -> None:
        if actual_return_datetime is not None and actual_return_datetime < departure_datetime:
            raise TripInvalidReturnDatetimeError("Actual return cannot be before departure")

    async def _get_or_raise(self, trip_id: uuid.UUID, tenant_id: uuid.UUID) -> Trip:
        trip = await self._repo.get_by_id(trip_id, tenant_id)
        if trip is None:
            raise TripNotFoundError("Trip not found")
        return trip

    async def _commit_or_raise(self) -> None:
        """Commit, translating a unique-constraint violation into a clean error.

        Catching the DB constraint here (rather than pre-checking with a
        SELECT) avoids a check-then-insert race between concurrent requests -
        the constraint is the actual source of truth for both trip_number
        uniqueness and the single-active-trip-per-boat rule.
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
        if constraint == "ix_trips_tenant_trip_number":
            return DuplicateTripNumberError("A trip with this trip number already exists")
        if constraint == "ix_trips_boat_single_active":
            return TripBoatAlreadyActiveError("This boat already has an active trip")
        return ConflictError("This operation conflicts with existing data")

    @staticmethod
    def _to_response(trip: Trip) -> TripResponse:
        return TripResponse.model_validate(trip)
