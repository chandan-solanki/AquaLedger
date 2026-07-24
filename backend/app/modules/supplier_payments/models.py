import datetime as dt
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from app.db.base import Base, TimestampMixin
from app.modules.supplier_payments.constants import PaymentMethod, SupplierPaymentStatus

if TYPE_CHECKING:
    from app.modules.purchase.models import PurchaseBill
    from app.modules.suppliers.models import Supplier


class SupplierPayment(TimestampMixin, Base):
    """A payment made to a supplier, optionally allocated across one or more
    purchase bills (ARCHITECTURE.md §5.2/§14, mirroring `Payment`'s shape on
    the buy side).

    Sprint 12 Session 1 - schema foundation only; no CRUD, allocation,
    posting or outstanding-update logic yet (see TASKS.md). Soft-deleted
    (ARCHITECTURE.md §38), though - mirroring Payment's own docstring - only
    DRAFT supplier payments are ever expected to be deleted: CLAUDE.md's
    "Payments are never deleted" business rule applies once a payment is
    POSTED, the same immutability boundary PurchaseBill draws at `posted`.

    `payment_number` is nullable for the same reason `payment_number` is on
    `Payment` (ARCHITECTURE.md §13.1): numbers are assigned only at posting
    (TASKS.md Session 5), never at draft creation, so an abandoned draft
    never punches a hole in the sequence. `posted_at` is provisioned now for
    that same future session, the same way `PurchaseBill.posted_at` was
    provisioned in its own Session 1.

    `allocated_amount`/`unallocated_amount` are plain application-maintained
    columns, not DB `GENERATED` expressions - consistent with how
    `Payment.allocated_amount`/`unallocated_amount` are handled
    (ARCHITECTURE.md §5.3): denormalized caches kept in sync by the service
    layer (Session 3/4), always re-derivable from `amount - allocated_amount`.
    """

    __tablename__ = "supplier_payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False
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
    status: Mapped[SupplierPaymentStatus] = mapped_column(
        String(20), nullable=False, server_default=SupplierPaymentStatus.DRAFT
    )
    posted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    supplier: Mapped["Supplier"] = relationship(back_populates="supplier_payments")
    allocations: Mapped[list["SupplierPaymentAllocation"]] = relationship(
        back_populates="supplier_payment"
    )

    __table_args__ = (
        Index("ix_supplier_payments_tenant", "tenant_id", postgresql_where=deleted_at.is_(None)),
        Index(
            "ix_supplier_payments_tenant_supplier",
            "tenant_id",
            "supplier_id",
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "ix_supplier_payments_tenant_status",
            "tenant_id",
            "status",
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "ix_supplier_payments_tenant_payment_date",
            "tenant_id",
            "payment_date",
            postgresql_where=deleted_at.is_(None),
        ),
        # Numbers are only unique once assigned (NULL while draft) - see the
        # payment_number docstring note above.
        Index(
            "ix_supplier_payments_tenant_payment_number",
            "tenant_id",
            "payment_number",
            unique=True,
            postgresql_where=deleted_at.is_(None) & payment_number.isnot(None),
        ),
    )


class SupplierPaymentAllocation(Base):
    """One application of a supplier payment against a purchase bill
    (ARCHITECTURE.md §5.2/§14.2, mirroring `PaymentAllocation`'s shape on the
    buy side) - the many-to-many join that lets a single supplier payment
    settle several purchase bills, or sit unallocated as on-account credit.

    Sprint 12 Session 1 - schema foundation only; allocation CRUD and the
    locking/validation transaction that keeps `SupplierPayment.
    allocated_amount` and `PurchaseBill.paid_amount` in sync land in
    Sessions 3/4 (see TASKS.md).

    Append-only, like `PaymentAllocation` (ARCHITECTURE.md §5.2): no
    `updated_at`, no soft delete - CLAUDE.md's "Ledger entries are
    append-only" / "Financial corrections must use reversal entries" applies
    equally here, so this deliberately does not use `TimestampMixin`.
    """

    __tablename__ = "supplier_payment_allocations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    supplier_payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_payments.id"), nullable=False
    )
    purchase_bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_bills.id"), nullable=False
    )
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    supplier_payment: Mapped["SupplierPayment"] = relationship(back_populates="allocations")
    purchase_bill: Mapped["PurchaseBill"] = relationship(
        back_populates="supplier_payment_allocations"
    )

    __table_args__ = (
        Index("ix_supplier_payment_allocations_tenant", "tenant_id"),
        Index(
            "ix_supplier_payment_allocations_tenant_supplier_payment",
            "tenant_id",
            "supplier_payment_id",
        ),
        Index(
            "ix_supplier_payment_allocations_tenant_purchase_bill",
            "tenant_id",
            "purchase_bill_id",
        ),
        # ARCHITECTURE.md §5.2's `payment_allocations` UNIQUE(payment_id,
        # invoice_id), applied on the buy side: a supplier payment allocates
        # to a given purchase bill at most once; a second allocation against
        # the same bill must adjust the existing row, not insert a new one.
        Index(
            "ix_supplier_payment_allocations_payment_bill",
            "supplier_payment_id",
            "purchase_bill_id",
            unique=True,
        ),
    )


class SupplierPaymentSequence(Base):
    """Per-tenant/prefix/fiscal-year supplier payment numbering counter
    (ARCHITECTURE.md §13.1, mirroring `payment_sequences`/`purchase_sequences`
    exactly).

    Allocation/incrementing logic (`SELECT ... FOR UPDATE` inside the
    Session 5 posting transaction) is not implemented yet - this session
    only creates the table shape. No soft-delete or audit columns - a pure
    counter, not a business record.
    """

    __tablename__ = "supplier_payment_sequences"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), primary_key=True
    )
    prefix: Mapped[str] = mapped_column(String(10), primary_key=True)
    fiscal_year: Mapped[str] = mapped_column(String(7), primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
