import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from app.db.base import Base, TimestampMixin


class CompanyProfile(TimestampMixin, Base):
    """The current tenant's own business identity - legal name, address,
    tax ids and logo - used to brand generated documents and reports
    (Sprint 14). Not to be confused with `app.modules.companies.Company`,
    which models customer/supplier business-party records.

    Exactly one row per tenant, enforced by the unique index on
    tenant_id below - `CompanyProfileService.get()` auto-vivifies this
    row on first access (seeded from `Tenant.name`), so callers never
    need a separate create/update branch. Never soft-deleted: the row
    itself is permanent once a tenant exists, only its logo sub-fields
    are ever cleared (see delete_logo).
    """

    __tablename__ = "company_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )

    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    company_code: Mapped[str | None] = mapped_column(String(50))

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
    website: Mapped[str | None] = mapped_column(String(255))

    gstin: Mapped[str | None] = mapped_column(String(15))
    pan: Mapped[str | None] = mapped_column(String(10))

    # Logo: only a storage key + its content-type is kept here - the bytes
    # themselves live in StorageService (app.core.document_engine.storage),
    # never in this table, matching how every other generated/uploaded
    # file in this codebase is stored.
    logo_storage_key: Mapped[str | None] = mapped_column(String(500))
    logo_content_type: Mapped[str | None] = mapped_column(String(50))
    logo_uploaded_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (Index("ix_company_profiles_tenant_id", "tenant_id", unique=True),)
