import datetime as dt
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db.base import Base, TimestampMixin
from app.modules.trip_expenses.constants import ExpenseType

if TYPE_CHECKING:
    from app.modules.trips.models import Trip


class TripExpense(TimestampMixin, Base):
    """Operational expense incurred during a fishing trip (ARCHITECTURE.md
    §5.2 `trip_expenses`).

    Sprint 8 Session 1 - schema foundation only; no CRUD endpoints yet
    (see TASKS.md). Soft-deleted (ARCHITECTURE.md §38 - expenses feed
    trip profitability calculations and must remain auditable).
    """

    __tablename__ = "trip_expenses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id"), nullable=False
    )

    expense_type: Mapped[ExpenseType] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    expense_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    vendor_name: Mapped[str | None] = mapped_column(String(255))
    receipt_number: Mapped[str | None] = mapped_column(String(100))

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    trip: Mapped["Trip"] = relationship(back_populates="trip_expenses")

    __table_args__ = (
        Index("ix_trip_expenses_tenant", "tenant_id", postgresql_where=deleted_at.is_(None)),
        Index(
            "ix_trip_expenses_tenant_trip",
            "tenant_id",
            "trip_id",
            postgresql_where=deleted_at.is_(None),
        ),
    )
