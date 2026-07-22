import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db.base import Base, TimestampMixin
from app.modules.trips.constants import ACTIVE_TRIP_STATUSES, TripStatus, TripType

if TYPE_CHECKING:
    from app.modules.boats.models import Boat
    from app.modules.trip_catches.models import TripCatch


class Trip(TimestampMixin, Base):
    """One fishing/transport journey performed by a boat (ARCHITECTURE.md §5.2 `trips`).

    Sprint 6 Session 1 - schema foundation only; no catch/expense/invoice
    linkage yet (see TASKS.md). Soft-deleted (ARCHITECTURE.md §38 -
    referenced by future expense/catch history).
    """

    __tablename__ = "trips"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    boat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("boats.id"), nullable=False
    )
    trip_number: Mapped[str] = mapped_column(String(50), nullable=False)
    trip_type: Mapped[TripType] = mapped_column(String(20), nullable=False)
    captain_name: Mapped[str | None] = mapped_column(String(255))
    departure_port: Mapped[str | None] = mapped_column(String(100))
    arrival_port: Mapped[str | None] = mapped_column(String(100))
    departure_datetime: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_return_datetime: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    actual_return_datetime: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[TripStatus] = mapped_column(
        String(20), nullable=False, server_default=TripStatus.PLANNED
    )
    notes: Mapped[str | None] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    boat: Mapped["Boat"] = relationship(back_populates="trips")
    trip_catches: Mapped[list["TripCatch"]] = relationship(back_populates="trip")

    __table_args__ = (
        Index(
            "ix_trips_tenant_trip_number",
            "tenant_id",
            "trip_number",
            unique=True,
            postgresql_where=deleted_at.is_(None),
        ),
        Index("ix_trips_tenant", "tenant_id", postgresql_where=deleted_at.is_(None)),
        Index(
            "ix_trips_tenant_boat",
            "tenant_id",
            "boat_id",
            postgresql_where=deleted_at.is_(None),
        ),
        # Session 4 business rule ("a boat cannot have more than one active
        # trip") enforced at the database, not just in the service layer -
        # a SELECT-then-INSERT check has a race window between concurrent
        # requests; this index makes Postgres itself the source of truth,
        # the same way ix_trips_tenant_trip_number does for trip_number.
        # No tenant_id needed: boat_id (a UUID PK on another table) is
        # already globally unique, so it can't collide across tenants.
        Index(
            "ix_trips_boat_single_active",
            "boat_id",
            unique=True,
            postgresql_where=status.in_(ACTIVE_TRIP_STATUSES) & deleted_at.is_(None),
        ),
    )
