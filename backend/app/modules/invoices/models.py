import datetime as dt
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db.base import Base, TimestampMixin
from app.modules.invoices.constants import InvoiceStatus

if TYPE_CHECKING:
    from app.modules.companies.models import Company
    from app.modules.fish.models import Fish
    from app.modules.trip_catches.models import TripCatch


class Invoice(TimestampMixin, Base):
    """Sales invoice billed to a company (ARCHITECTURE.md §5.2 `invoices`).

    Sprint 9 Session 1 - schema foundation only; no CRUD or issue-workflow
    endpoints yet (see TASKS.md). Soft-deleted (ARCHITECTURE.md §38 -
    referenced by future payment/ledger history), though only DRAFT invoices
    are ever expected to be deleted - ISSUED invoices are immutable
    (ARCHITECTURE.md §13.2) and corrected via credit notes, not deletion.

    `invoice_number` is nullable: numbers are assigned at issue, never at
    draft creation, so abandoned drafts don't punch permanent holes in the
    sequence (ARCHITECTURE.md §13.1). `issued_at` is provisioned now for the
    same reason trip_catches' available_quantity/sold_quantity/waste_quantity
    were provisioned in its Session 1 - the Session 5 issue workflow needs it
    and it belongs to this schema unit.

    `invoice_type` (sales | credit_note | proforma) and `parent_invoice_id`
    from ARCHITECTURE.md §5.2 are deferred: credit notes are out of scope for
    this sprint's six sessions (TASKS.md), so only plain sales invoices are
    modeled for now - the same as-built simplification trip_catches applied
    to `grade`/`boxes`/`estimated_rate`.

    `balance_amount` is a plain application-maintained column, not a DB
    `GENERATED` expression - consistent with how `companies.outstanding_amount`
    is handled elsewhere (§5.3): a denormalized cache kept in sync by the
    service layer within the same transaction as its source change, always
    re-derivable from `total_amount - paid_amount`.
    """

    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )

    invoice_number: Mapped[str | None] = mapped_column(String(50))
    invoice_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    due_date: Mapped[dt.date | None] = mapped_column(Date)

    status: Mapped[InvoiceStatus] = mapped_column(
        String(20), nullable=False, server_default=InvoiceStatus.DRAFT
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
    issued_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    company: Mapped["Company"] = relationship(back_populates="invoices")
    items: Mapped[list["InvoiceItem"]] = relationship(
        back_populates="invoice", order_by="InvoiceItem.line_number"
    )

    __table_args__ = (
        Index("ix_invoices_tenant", "tenant_id", postgresql_where=deleted_at.is_(None)),
        Index(
            "ix_invoices_tenant_company",
            "tenant_id",
            "company_id",
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "ix_invoices_tenant_status",
            "tenant_id",
            "status",
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "ix_invoices_tenant_invoice_date",
            "tenant_id",
            "invoice_date",
            postgresql_where=deleted_at.is_(None),
        ),
        # Numbers are only unique once assigned (NULL while draft) - see the
        # invoice_number docstring note above.
        Index(
            "ix_invoices_tenant_invoice_number",
            "tenant_id",
            "invoice_number",
            unique=True,
            postgresql_where=deleted_at.is_(None) & invoice_number.isnot(None),
        ),
    )


class InvoiceItem(TimestampMixin, Base):
    """One line of an invoice (ARCHITECTURE.md §5.2 `invoice_items`).

    Sprint 9 Session 1 - schema foundation only; item CRUD and validation
    land in Session 3, financial calculation in Session 4 (see TASKS.md).
    Soft-deleted for the same audit reasons as its parent invoice.

    `trip_catch_id` is nullable: it links a sold line back to the trip catch
    it was realized from (ARCHITECTURE.md §16.1's "realized revenue" model)
    when the fish sold came from a tracked trip; lines for purchased/
    untracked stock leave it NULL.

    `unit` is a plain string snapshot of the unit sold on this line, not a
    foreign key or shared enum with `fish.unit` - an invoice line is a
    historical record and must not silently change if the fish master's
    default unit is edited later.
    """

    __tablename__ = "invoice_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)

    fish_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fish.id"), nullable=False
    )
    trip_catch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trip_catches.id")
    )
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

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    invoice: Mapped["Invoice"] = relationship(back_populates="items")
    fish: Mapped["Fish"] = relationship(back_populates="invoice_items")
    trip_catch: Mapped["TripCatch | None"] = relationship(back_populates="invoice_items")

    __table_args__ = (
        Index("ix_invoice_items_tenant", "tenant_id", postgresql_where=deleted_at.is_(None)),
        Index(
            "ix_invoice_items_tenant_invoice",
            "tenant_id",
            "invoice_id",
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "ix_invoice_items_tenant_fish",
            "tenant_id",
            "fish_id",
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "ix_invoice_items_tenant_trip_catch",
            "tenant_id",
            "trip_catch_id",
            postgresql_where=deleted_at.is_(None),
        ),
    )


class InvoiceSequence(Base):
    """Per-tenant/prefix/fiscal-year invoice numbering counter
    (ARCHITECTURE.md §13.1, §5.2 `invoice_sequences`).

    Allocated and incremented only inside the Session 5 issue transaction
    (`SELECT ... FOR UPDATE` on this row, see InvoiceService._allocate_invoice_number)
    - never at draft creation, so abandoned drafts never punch a hole in the
    sequence. Postgres sequences are deliberately not used here: they are
    non-transactional and gap on rollback, exactly what §13.1 says must be
    avoided for GST audit compliance.

    No soft-delete or audit columns - this is a pure counter, not a business
    record; nothing ever looks its rows up except the numbering allocation
    itself.
    """

    __tablename__ = "invoice_sequences"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), primary_key=True
    )
    prefix: Mapped[str] = mapped_column(String(10), primary_key=True)
    fiscal_year: Mapped[str] = mapped_column(String(7), primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
