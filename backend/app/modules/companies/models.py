import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from app.db.base import Base, TimestampMixin
from app.modules.companies.constants import CompanyStatus, CompanyType, OpeningBalanceType


class Company(TimestampMixin, Base):
    """Customers, suppliers and companies that buy or sell fish.

    Soft-deleted (ARCHITECTURE.md §38 - referenced by invoice/payment history).
    `outstanding_amount` is a denormalized cache maintained by the invoicing/
    payments modules (§5.3); it is not written to here.
    """

    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255))
    gstin: Mapped[str | None] = mapped_column(String(15))
    pan: Mapped[str | None] = mapped_column(String(10))

    address_line1: Mapped[str | None] = mapped_column(String(255))
    address_line2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    state_code: Mapped[str | None] = mapped_column(String(2))
    pincode: Mapped[str | None] = mapped_column(String(10))
    country: Mapped[str | None] = mapped_column(String(100))

    phone: Mapped[str | None] = mapped_column(String(20))
    alt_phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    contact_person: Mapped[str | None] = mapped_column(String(255))

    company_type: Mapped[CompanyType] = mapped_column(String(20), nullable=False)

    credit_limit: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )
    credit_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )
    opening_balance_date: Mapped[dt.date | None] = mapped_column(Date)
    opening_balance_type: Mapped[OpeningBalanceType | None] = mapped_column(String(10))

    outstanding_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )

    status: Mapped[CompanyStatus] = mapped_column(
        String(20), nullable=False, server_default=CompanyStatus.ACTIVE
    )
    notes: Mapped[str | None] = mapped_column(Text)

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (
        Index(
            "ix_companies_tenant_code",
            "tenant_id",
            "code",
            unique=True,
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "ix_companies_tenant_name",
            "tenant_id",
            func.lower(name),
            unique=True,
            postgresql_where=deleted_at.is_(None),
        ),
        Index("ix_companies_tenant", "tenant_id", postgresql_where=deleted_at.is_(None)),
    )
