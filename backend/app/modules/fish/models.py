import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from app.db.base import Base, TimestampMixin
from app.modules.fish.constants import FishUnit


class Fish(TimestampMixin, Base):
    """Fish master data - species/products traded, not stock or pricing history.

    Soft-deleted (ARCHITECTURE.md §38 - referenced by future invoice/trip
    history).
    """

    __tablename__ = "fish"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    local_name: Mapped[str | None] = mapped_column(String(255))
    scientific_name: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(100))
    unit: Mapped[FishUnit] = mapped_column(String(20), nullable=False, server_default=FishUnit.KG)

    default_purchase_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    default_sale_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))

    hsn_code: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (
        Index(
            "ix_fish_tenant_code",
            "tenant_id",
            "code",
            unique=True,
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "ix_fish_tenant_name",
            "tenant_id",
            func.lower(name),
            unique=True,
            postgresql_where=deleted_at.is_(None),
        ),
        Index("ix_fish_tenant", "tenant_id", postgresql_where=deleted_at.is_(None)),
    )
