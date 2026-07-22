import datetime as dt
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db.base import Base, TimestampMixin
from app.modules.trip_catches.constants import CatchGrade

if TYPE_CHECKING:
    from app.modules.fish.models import Fish
    from app.modules.invoices.models import InvoiceItem
    from app.modules.trips.models import Trip


class TripCatch(TimestampMixin, Base):
    """Fish landed on a trip (ARCHITECTURE.md §5.2 `trip_catches`).

    Sprint 7 Session 1 - schema foundation only; no CRUD endpoints yet
    (see TASKS.md). Soft-deleted (ARCHITECTURE.md §38 - referenced by
    future invoice line linkage).
    """

    __tablename__ = "trip_catches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id"), nullable=False
    )
    fish_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fish.id"), nullable=False
    )
    grade: Mapped[CatchGrade | None] = mapped_column(String(1))

    quantity_caught: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    available_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, server_default="0"
    )
    sold_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, server_default="0"
    )
    waste_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, server_default="0"
    )

    landing_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    landing_port: Mapped[str | None] = mapped_column(String(100))

    remarks: Mapped[str | None] = mapped_column(Text)

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    trip: Mapped["Trip"] = relationship(back_populates="trip_catches")
    fish: Mapped["Fish"] = relationship(back_populates="trip_catches")
    invoice_items: Mapped[list["InvoiceItem"]] = relationship(back_populates="trip_catch")

    __table_args__ = (
        Index("ix_trip_catches_tenant", "tenant_id", postgresql_where=deleted_at.is_(None)),
        Index(
            "ix_trip_catches_tenant_trip",
            "tenant_id",
            "trip_id",
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "ix_trip_catches_tenant_fish",
            "tenant_id",
            "fish_id",
            postgresql_where=deleted_at.is_(None),
        ),
        # Defense in depth for the Session 3 quantity invariant
        # (TripCatchService._ensure_quantity_invariant): SELECT ... FOR
        # UPDATE (TripCatchRepository.get_by_id_for_update) is what actually
        # prevents the concurrent lost-update race, but this constraint
        # guarantees no writer - buggy application code, a future bulk
        # operation, a raw SQL script - can ever persist a row where the
        # sum doesn't add up, DB-enforced the same way
        # ix_trips_boat_single_active enforces the boat-availability rule.
        CheckConstraint(
            "available_quantity + sold_quantity + waste_quantity = quantity_caught",
            name="ck_trip_catches_quantity_invariant",
        ),
    )
