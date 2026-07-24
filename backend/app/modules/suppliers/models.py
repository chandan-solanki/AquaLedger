import datetime as dt
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db.base import Base, TimestampMixin
from app.modules.suppliers.constants import SupplierStatus

if TYPE_CHECKING:
    from app.modules.purchase.models import PurchaseBill
    from app.modules.supplier_payments.models import SupplierPayment


class Supplier(TimestampMixin, Base):
    """A supplier/vendor that sells fish or goods to the tenant
    (Sprint 11 Session 1 - TASKS.md).

    Schema foundation only - no CRUD, search or business logic yet. Soft-
    deleted (ARCHITECTURE.md §38), mirroring Company's own docstring: a
    supplier referenced by purchase bill history is never hard-deleted.

    Unlike `companies` (which models both customers and suppliers with a
    `company_type` discriminator), suppliers are their own table per this
    sprint's as-built design (TASKS.md) - a single `address` free-text field
    rather than Company's structured address_line1/2/city/state/pincode
    split, and no `credit_limit`/`pan`/`opening_balance_date` columns, since
    TASKS.md's field list doesn't ask for them.
    """

    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255))
    gstin: Mapped[str | None] = mapped_column(String(15))
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))
    contact_person: Mapped[str | None] = mapped_column(String(255))

    credit_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )
    outstanding_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )

    status: Mapped[SupplierStatus] = mapped_column(
        String(20), nullable=False, server_default=SupplierStatus.ACTIVE
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    purchase_bills: Mapped[list["PurchaseBill"]] = relationship(back_populates="supplier")
    supplier_payments: Mapped[list["SupplierPayment"]] = relationship(back_populates="supplier")

    __table_args__ = (
        Index("ix_suppliers_tenant", "tenant_id", postgresql_where=deleted_at.is_(None)),
        Index(
            "ix_suppliers_tenant_code",
            "tenant_id",
            "code",
            unique=True,
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "ix_suppliers_tenant_name",
            "tenant_id",
            func.lower(name),
            unique=True,
            postgresql_where=deleted_at.is_(None),
        ),
    )
