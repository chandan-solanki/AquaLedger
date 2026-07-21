import datetime as dt
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.companies.models import Company
    from app.modules.trips.models import Trip


class Boat(TimestampMixin, Base):
    """Fishing boats owned by a company (ARCHITECTURE.md §5.2 `boats`).

    Sprint 5 - boat master data only; no trip/catch/invoice logic yet
    (see TASKS.md). Soft-deleted (ARCHITECTURE.md §38 - referenced by
    future trip history).
    """

    __tablename__ = "boats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    registration_number: Mapped[str] = mapped_column(String(50), nullable=False)
    license_number: Mapped[str | None] = mapped_column(String(50))
    boat_type: Mapped[str | None] = mapped_column(String(50))
    capacity_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    engine_number: Mapped[str | None] = mapped_column(String(50))
    engine_hp: Mapped[int | None] = mapped_column(Integer)
    captain_name: Mapped[str | None] = mapped_column(String(255))
    captain_phone: Mapped[str | None] = mapped_column(String(20))
    insurance_expiry: Mapped[dt.date | None] = mapped_column(Date)
    license_expiry: Mapped[dt.date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    company: Mapped["Company"] = relationship(back_populates="boats")
    trips: Mapped[list["Trip"]] = relationship(back_populates="boat")

    __table_args__ = (
        Index(
            "ix_boats_tenant_code",
            "tenant_id",
            "code",
            unique=True,
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "ix_boats_tenant_registration",
            "tenant_id",
            "registration_number",
            unique=True,
            postgresql_where=deleted_at.is_(None),
        ),
        Index("ix_boats_tenant", "tenant_id", postgresql_where=deleted_at.is_(None)),
        Index(
            "ix_boats_tenant_company",
            "tenant_id",
            "company_id",
            postgresql_where=deleted_at.is_(None),
        ),
    )
