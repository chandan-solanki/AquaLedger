import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db.base import Base, TimestampMixin
from app.modules.delivery_challans.constants import DeliveryChallanStatus


class DeliveryChallan(TimestampMixin, Base):
    """A delivery challan - the physical dispatch/delivery of goods already
    invoiced to a customer (Sprint 12 Session 14). Deliberately NOT a
    financial document: it carries no subtotal/tax/total_amount, and
    creating, dispatching, delivering, or cancelling one never touches
    Company.outstanding_amount, Invoice.balance_amount/paid_amount, ledger,
    or any financial report - those remain driven exclusively by Invoice
    issue and Payment allocation.

    `invoice_id` is required (unlike PurchaseBill.purchase_order_id, which is
    optional only because standalone bills were the pre-existing flow that
    had to keep working) - a delivery challan has no such backward-
    compatibility constraint, and the whole point of this document is to
    record delivery against an already-issued invoice. There is deliberately
    no `company_id` column here either: since the invoice link is mandatory,
    the customer is always read via the linked invoice
    (`InvoiceService.get(...).company_id`), never duplicated - a duplicated
    copy could drift from the invoice's own company_id with no way to detect
    it. This is a bare FK column with no SQLAlchemy `relationship()` to
    `Invoice` - modules never hold ORM relationships across module
    boundaries (ARCHITECTURE.md §1.1/§2), mirroring
    `PurchaseBill.purchase_order_id` exactly.

    Soft-deleted (ARCHITECTURE.md §38), mirroring PurchaseOrder exactly -
    only DRAFT challans are ever expected to be deleted.

    `challan_number` is nullable for the same reason `po_number`/
    `bill_number`/`invoice_number` are: numbers are assigned only at
    dispatch - the transition where this document stops being a mutable
    draft and becomes a real, physical event - never at draft creation, so
    an abandoned draft never punches a hole in the sequence.

    `dispatched_at`/`delivered_at` are two separate lifecycle timestamps
    (unlike PurchaseOrder's single `confirmed_at`) because dispatch and
    delivery are two distinct, separately meaningful physical events for
    this document, not one "becomes real" moment.

    `next_item_line_number` is a durable counter (not `MAX(line_number)`),
    allocated via an atomic `UPDATE ... RETURNING`
    (DeliveryChallanRepository.allocate_next_line_number) - mirrors
    PurchaseOrder.next_item_line_number exactly, since DeliveryChallanItem is
    also hard-deleted.
    """

    __tablename__ = "delivery_challans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False
    )

    challan_number: Mapped[str | None] = mapped_column(String(50))
    challan_date: Mapped[dt.date] = mapped_column(Date, nullable=False)

    status: Mapped[DeliveryChallanStatus] = mapped_column(
        String(20), nullable=False, server_default=DeliveryChallanStatus.DRAFT
    )

    remarks: Mapped[str | None] = mapped_column(Text)
    dispatched_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    next_item_line_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    items: Mapped[list["DeliveryChallanItem"]] = relationship(
        back_populates="delivery_challan", order_by="DeliveryChallanItem.line_number"
    )

    __table_args__ = (
        Index("ix_delivery_challans_tenant", "tenant_id", postgresql_where=deleted_at.is_(None)),
        Index(
            "ix_delivery_challans_tenant_invoice",
            "tenant_id",
            "invoice_id",
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "ix_delivery_challans_tenant_status",
            "tenant_id",
            "status",
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "ix_delivery_challans_tenant_challan_date",
            "tenant_id",
            "challan_date",
            postgresql_where=deleted_at.is_(None),
        ),
        # Numbers are only unique once assigned (NULL while draft) - see the
        # challan_number docstring note above.
        Index(
            "ix_delivery_challans_tenant_challan_number",
            "tenant_id",
            "challan_number",
            unique=True,
            postgresql_where=deleted_at.is_(None) & challan_number.isnot(None),
        ),
    )


class DeliveryChallanItem(TimestampMixin, Base):
    """One line of a delivery challan (Sprint 12 Session 14), linking a
    delivered quantity back to the specific invoice item it was invoiced on.

    Deliberately carries no financial fields (no rate/tax/discount/
    line_total) - a delivery challan is logistics-only, never a financial
    document. `invoice_item_id` is required (not nullable): every challan
    item must reference the invoiced line it delivers against, since that is
    exactly what makes over-delivery protection possible. Like
    `PurchaseBillItem.purchase_order_item_id`, this is a bare FK column with
    no SQLAlchemy `relationship()` to `InvoiceItem` - a cross-module
    reference, never a cross-module ORM relationship.

    Hard-deleted (no soft-delete columns) - the same "line is a historical
    record, deleted outright rather than voided" posture
    PurchaseOrderItem/PurchaseBillItem take, since only DRAFT challans ever
    have their items mutated at all.

    `unit` is a plain string snapshot of the invoice item's own unit at the
    time this line was added, not a live join - safe because an invoice
    item's `unit` never changes once the invoice is issued (ARCHITECTURE.md
    §13.2's immutability rule), mirroring why InvoiceItem itself snapshots
    `unit` rather than joining to `fish.unit`.
    """

    __tablename__ = "delivery_challan_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    delivery_challan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("delivery_challans.id"), nullable=False
    )
    invoice_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoice_items.id"), nullable=False
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)

    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)

    delivery_challan: Mapped["DeliveryChallan"] = relationship(back_populates="items")

    __table_args__ = (
        Index("ix_delivery_challan_items_tenant", "tenant_id"),
        Index("ix_delivery_challan_items_tenant_challan", "tenant_id", "delivery_challan_id"),
        Index("ix_delivery_challan_items_tenant_invoice_item", "tenant_id", "invoice_item_id"),
    )


class DeliveryChallanSequence(Base):
    """Per-tenant/prefix/fiscal-year delivery challan numbering counter,
    mirroring `PurchaseOrderSequence`/`PurchaseSequence`/`InvoiceSequence`
    exactly. No soft-delete or audit columns - a pure counter, not a
    business record.
    """

    __tablename__ = "delivery_challan_sequences"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), primary_key=True
    )
    prefix: Mapped[str] = mapped_column(String(10), primary_key=True)
    fiscal_year: Mapped[str] = mapped_column(String(7), primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
