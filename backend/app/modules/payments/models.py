import datetime as dt
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db.base import Base, TimestampMixin
from app.modules.payments.constants import PaymentMethod, PaymentStatus

if TYPE_CHECKING:
    from app.modules.companies.models import Company
    from app.modules.invoices.models import Invoice


class Payment(TimestampMixin, Base):
    """A payment received from a company, optionally allocated across one or
    more invoices (ARCHITECTURE.md §5.2 `payments`, §14).

    Sprint 10 Session 1 - schema foundation only; no CRUD, allocation,
    posting or outstanding-update logic yet (see TASKS.md). Soft-deleted
    (ARCHITECTURE.md §38), though - mirroring Invoice's own docstring - only
    DRAFT payments are ever expected to be deleted: CLAUDE.md's "Payments are
    never deleted" business rule applies once a payment is POSTED, the same
    immutability boundary Invoice draws at `issued`.

    `payment_number` is nullable for the same reason `invoice_number` is
    (ARCHITECTURE.md §13.1): numbers are assigned only at posting (TASKS.md
    Session 5), never at draft creation, so an abandoned draft never punches
    a hole in the sequence.

    `direction` (received | paid) and cheque-specific fields
    (`cheque_status`, `cleared_at`) from ARCHITECTURE.md §5.2 are deferred -
    out of scope for this sprint's six sessions (TASKS.md), the same kind of
    as-built simplification Invoice applied to `invoice_type`/
    `parent_invoice_id`. Only customer-received payments are modeled for now.

    `allocated_amount`/`unallocated_amount` are plain application-maintained
    columns, not DB `GENERATED` expressions - consistent with how
    `Invoice.balance_amount` and `Company.outstanding_amount` are handled
    (ARCHITECTURE.md §5.3): denormalized caches kept in sync by the service
    layer (Session 3/4), always re-derivable from `amount - allocated_amount`.
    """

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )

    payment_number: Mapped[str | None] = mapped_column(String(50))
    payment_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(String(20), nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(100))
    bank_name: Mapped[str | None] = mapped_column(String(255))

    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    allocated_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )
    unallocated_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    remarks: Mapped[str | None] = mapped_column(Text)
    status: Mapped[PaymentStatus] = mapped_column(
        String(20), nullable=False, server_default=PaymentStatus.DRAFT
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    company: Mapped["Company"] = relationship(back_populates="payments")
    allocations: Mapped[list["PaymentAllocation"]] = relationship(back_populates="payment")

    __table_args__ = (
        Index("ix_payments_tenant", "tenant_id", postgresql_where=deleted_at.is_(None)),
        Index(
            "ix_payments_tenant_company",
            "tenant_id",
            "company_id",
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "ix_payments_tenant_status",
            "tenant_id",
            "status",
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "ix_payments_tenant_payment_date",
            "tenant_id",
            "payment_date",
            postgresql_where=deleted_at.is_(None),
        ),
        # Numbers are only unique once assigned (NULL while draft) - see the
        # payment_number docstring note above.
        Index(
            "ix_payments_tenant_payment_number",
            "tenant_id",
            "payment_number",
            unique=True,
            postgresql_where=deleted_at.is_(None) & payment_number.isnot(None),
        ),
    )


class PaymentAllocation(Base):
    """One application of a payment against an invoice (ARCHITECTURE.md
    §5.2 `payment_allocations`, §14.2) - the many-to-many join that lets a
    single payment settle several invoices, or sit unallocated as on-account
    credit.

    Sprint 10 Session 1 - schema foundation only; allocation CRUD and the
    locking/validation transaction that keeps `Payment.allocated_amount` and
    `Invoice.paid_amount` in sync land in Sessions 3/4 (see TASKS.md).

    Append-only, like `ledger_entries` (ARCHITECTURE.md §5.2): no
    `updated_at`, no soft delete - CLAUDE.md's "Ledger entries are
    append-only" / "Financial corrections must use reversal entries" applies
    equally here, so this deliberately does not use `TimestampMixin`.
    `allocated_at`/`allocated_by` from ARCHITECTURE.md §5.2 are represented
    here as the plain audit pair `created_at`/`created_by`, matching the
    field list TASKS.md's Session 1 spec actually asks for.
    """

    __tablename__ = "payment_allocations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False
    )
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    payment: Mapped["Payment"] = relationship(back_populates="allocations")
    invoice: Mapped["Invoice"] = relationship(back_populates="payment_allocations")

    __table_args__ = (
        Index("ix_payment_allocations_tenant", "tenant_id"),
        Index("ix_payment_allocations_tenant_payment", "tenant_id", "payment_id"),
        Index("ix_payment_allocations_tenant_invoice", "tenant_id", "invoice_id"),
        # ARCHITECTURE.md §5.2: "UNIQUE(payment_id, invoice_id)" - a payment
        # allocates to a given invoice at most once; a second allocation
        # against the same invoice must adjust the existing row, not insert
        # a new one.
        Index(
            "ix_payment_allocations_payment_invoice",
            "payment_id",
            "invoice_id",
            unique=True,
        ),
    )


class PaymentSequence(Base):
    """Per-tenant/prefix/fiscal-year payment numbering counter
    (ARCHITECTURE.md §13.1, mirroring `invoice_sequences` exactly).

    Allocated and incremented only inside the Session 5 posting transaction
    (`SELECT ... FOR UPDATE` on this row, see
    PaymentService._allocate_payment_number) - never at draft creation, so
    an abandoned draft never punches a hole in the sequence. Postgres
    sequences are deliberately not used here, for the same GST-audit
    gap-avoidance reason InvoiceSequence's docstring gives.

    No soft-delete or audit columns - a pure counter, not a business record.
    """

    __tablename__ = "payment_sequences"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), primary_key=True
    )
    prefix: Mapped[str] = mapped_column(String(10), primary_key=True)
    fiscal_year: Mapped[str] = mapped_column(String(7), primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
