import datetime as dt
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db.base import Base, TimestampMixin
from app.modules.purchase_orders.constants import PurchaseOrderStatus

if TYPE_CHECKING:
    from app.modules.suppliers.models import Supplier


class PurchaseOrder(TimestampMixin, Base):
    """A purchase order - a procurement commitment/request to a supplier
    (Sprint 12 Session 9 - TASKS.md), mirroring `PurchaseBill`'s shape but
    deliberately NOT a financial document: it carries no `paid_amount`/
    `balance_amount` and confirming/fulfilling one never touches
    `Supplier.outstanding_amount`, ledger, or any financial report - those
    remain driven exclusively by Purchase Bills and Supplier Payments.

    Soft-deleted (ARCHITECTURE.md §38), mirroring PurchaseBill exactly -
    only DRAFT orders are ever expected to be deleted, the same
    immutability boundary PurchaseBill draws at `posted`.

    `po_number` is nullable for the same reason `bill_number`/
    `invoice_number` are (ARCHITECTURE.md §13.1): numbers are assigned only
    at confirmation, never at draft creation, so an abandoned draft never
    punches a hole in the sequence. `confirmed_at` is the single lifecycle
    timestamp provisioned (mirroring `posted_at`/`issued_at`) - there is no
    `cancelled_at`/`fulfilled_at`, the same as-built minimalism `Invoice`
    applies (no `cancelled_at` despite its own architecture sketch listing
    one).

    `next_item_line_number` is a durable counter (not `MAX(line_number)`),
    allocated via an atomic `UPDATE ... RETURNING`
    (PurchaseOrderRepository.allocate_next_line_number) - mirrors
    PurchaseBill.next_item_line_number exactly, since PurchaseOrderItem is
    also hard-deleted.
    """

    __tablename__ = "purchase_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False
    )

    po_number: Mapped[str | None] = mapped_column(String(50))
    order_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    expected_delivery_date: Mapped[dt.date | None] = mapped_column(Date)

    status: Mapped[PurchaseOrderStatus] = mapped_column(
        String(20), nullable=False, server_default=PurchaseOrderStatus.DRAFT
    )

    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, server_default="0")
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )
    taxable_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, server_default="0")
    transport_charge: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )
    other_charge: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )
    round_off: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, server_default="0")
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )

    remarks: Mapped[str | None] = mapped_column(Text)
    confirmed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    next_item_line_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    supplier: Mapped["Supplier"] = relationship(back_populates="purchase_orders")
    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        back_populates="purchase_order", order_by="PurchaseOrderItem.line_number"
    )

    __table_args__ = (
        Index("ix_purchase_orders_tenant", "tenant_id", postgresql_where=deleted_at.is_(None)),
        Index(
            "ix_purchase_orders_tenant_supplier",
            "tenant_id",
            "supplier_id",
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "ix_purchase_orders_tenant_status",
            "tenant_id",
            "status",
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "ix_purchase_orders_tenant_order_date",
            "tenant_id",
            "order_date",
            postgresql_where=deleted_at.is_(None),
        ),
        # Numbers are only unique once assigned (NULL while draft) - see the
        # po_number docstring note above.
        Index(
            "ix_purchase_orders_tenant_po_number",
            "tenant_id",
            "po_number",
            unique=True,
            postgresql_where=deleted_at.is_(None) & po_number.isnot(None),
        ),
    )


class PurchaseOrderItem(TimestampMixin, Base):
    """One line of a purchase order (Sprint 12 Session 9 - TASKS.md),
    mirroring `PurchaseBillItem`'s shape exactly.

    Deliberately carries no soft delete or created_by/updated_by/deleted_by
    columns and no `fish_id` foreign key - the same "line is a historical
    record" reasoning PurchaseBillItem's own docstring gives; `unit` is a
    plain string, not a shared enum with any fish master.
    """

    __tablename__ = "purchase_order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=False
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)

    description: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)

    discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, server_default="0"
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )
    taxable_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, server_default="0")
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, server_default="0")
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, server_default="0")

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="items")

    __table_args__ = (
        Index("ix_purchase_order_items_tenant", "tenant_id"),
        Index("ix_purchase_order_items_tenant_order", "tenant_id", "purchase_order_id"),
    )


class PurchaseOrderSequence(Base):
    """Per-tenant/prefix/fiscal-year purchase order numbering counter,
    mirroring `purchase_sequences`/`invoice_sequences`/`payment_sequences`
    exactly. No soft-delete or audit columns - a pure counter, not a
    business record.
    """

    __tablename__ = "purchase_order_sequences"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), primary_key=True
    )
    prefix: Mapped[str] = mapped_column(String(10), primary_key=True)
    fiscal_year: Mapped[str] = mapped_column(String(7), primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
