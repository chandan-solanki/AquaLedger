import datetime as dt
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db.base import Base, TimestampMixin
from app.modules.purchase.constants import PurchaseStatus

if TYPE_CHECKING:
    from app.modules.supplier_payments.models import SupplierPaymentAllocation
    from app.modules.suppliers.models import Supplier


class PurchaseBill(TimestampMixin, Base):
    """A purchase bill received from a supplier (Sprint 11 Session 1 -
    TASKS.md), mirroring `Invoice`'s shape on the buy side.

    Schema foundation only - no CRUD, item management, financial
    calculation or posting workflow yet (those land in Sessions 2-5). Soft-
    deleted (ARCHITECTURE.md §38), though only DRAFT bills are ever expected
    to be deleted - the same immutability boundary Invoice draws at
    `issued` and Payment draws at `posted`.

    `bill_number` is nullable for the same reason `invoice_number` is
    (ARCHITECTURE.md §13.1): numbers are assigned only at posting (Session
    5), never at draft creation, so an abandoned draft never punches a hole
    in the sequence. `posted_at` is provisioned now for that same future
    session, the same way `issued_at` was provisioned in Invoice's own
    Session 1.

    `taxable_amount` was added in Session 4 (TASKS.md) alongside the
    financial engine - Session 1's field list didn't ask for it, but Session
    4's "PURCHASE BILL CALCULATIONS" explicitly lists `taxable_amount =
    SUM(item.taxable_amount)` as a bill-level total, the same aggregate
    `invoices.taxable_amount` stores.
    """

    __tablename__ = "purchase_bills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False
    )

    bill_number: Mapped[str | None] = mapped_column(String(50))
    bill_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    due_date: Mapped[dt.date | None] = mapped_column(Date)

    status: Mapped[PurchaseStatus] = mapped_column(
        String(20), nullable=False, server_default=PurchaseStatus.DRAFT
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
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, server_default="0")
    balance_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )

    remarks: Mapped[str | None] = mapped_column(Text)
    posted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    # Sprint 11 Session 3: PurchaseBillItem has no soft-delete columns (see
    # its own docstring), so a hard-deleted item's line_number cannot be
    # recovered from MAX(line_number) the way InvoiceItem's next_line_number
    # does. This counter is the durable source of the next line_number -
    # allocated via an atomic UPDATE ... RETURNING (PurchaseRepository.
    # allocate_next_line_number), so it only ever advances and a number is
    # never reused even if every item on the bill is deleted.
    next_item_line_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    supplier: Mapped["Supplier"] = relationship(back_populates="purchase_bills")
    items: Mapped[list["PurchaseBillItem"]] = relationship(
        back_populates="purchase_bill", order_by="PurchaseBillItem.line_number"
    )
    supplier_payment_allocations: Mapped[list["SupplierPaymentAllocation"]] = relationship(
        back_populates="purchase_bill"
    )

    __table_args__ = (
        Index("ix_purchase_bills_tenant", "tenant_id", postgresql_where=deleted_at.is_(None)),
        Index(
            "ix_purchase_bills_tenant_supplier",
            "tenant_id",
            "supplier_id",
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "ix_purchase_bills_tenant_status",
            "tenant_id",
            "status",
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "ix_purchase_bills_tenant_bill_date",
            "tenant_id",
            "bill_date",
            postgresql_where=deleted_at.is_(None),
        ),
        # Numbers are only unique once assigned (NULL while draft) - see the
        # bill_number docstring note above.
        Index(
            "ix_purchase_bills_tenant_bill_number",
            "tenant_id",
            "bill_number",
            unique=True,
            postgresql_where=deleted_at.is_(None) & bill_number.isnot(None),
        ),
    )


class PurchaseBillItem(TimestampMixin, Base):
    """One line of a purchase bill (Sprint 11 Session 1 - TASKS.md),
    mirroring `InvoiceItem`'s shape on the buy side.

    Schema foundation only - item CRUD lands in Session 3, financial
    calculation in Session 4 (see TASKS.md). Deliberately carries no soft
    delete or created_by/updated_by/deleted_by columns and no `fish_id`
    foreign key - TASKS.md's Session 1 field list for `purchase_bill_items`
    lists only `created_at`/`updated_at` (via TimestampMixin) alongside its
    business fields, unlike `invoice_items`' fuller audit trail; `unit` is a
    plain string, not a shared enum with any fish master, for the same
    "line is a historical record" reason InvoiceItem's own docstring gives.
    """

    __tablename__ = "purchase_bill_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    purchase_bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_bills.id"), nullable=False
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

    purchase_bill: Mapped["PurchaseBill"] = relationship(back_populates="items")

    __table_args__ = (
        Index("ix_purchase_bill_items_tenant", "tenant_id"),
        Index("ix_purchase_bill_items_tenant_bill", "tenant_id", "purchase_bill_id"),
    )


class PurchaseSequence(Base):
    """Per-tenant/prefix/fiscal-year purchase bill numbering counter
    (placeholder table - TASKS.md Sprint 11 Session 1), mirroring
    `invoice_sequences`/`payment_sequences` exactly.

    Allocation/incrementing logic (`SELECT ... FOR UPDATE` inside the
    Session 5 posting transaction) is not implemented yet - this session
    only creates the table shape. No soft-delete or audit columns - a pure
    counter, not a business record.
    """

    __tablename__ = "purchase_sequences"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), primary_key=True
    )
    prefix: Mapped[str] = mapped_column(String(10), primary_key=True)
    fiscal_year: Mapped[str] = mapped_column(String(7), primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
