import uuid
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Tenant
from app.modules.suppliers.constants import SupplierStatus
from app.modules.suppliers.models import Supplier


@pytest.fixture
async def tenant_id(db_session: AsyncSession) -> uuid.UUID:
    """A fresh tenant per test, mirroring test_company_repository.py's
    fixture - keeps unique-index assertions isolated from the seeded
    default tenant's data."""
    tenant = Tenant(name="Supplier Test Tenant", slug=f"supplier-test-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    await db_session.commit()
    return tenant.id


async def _make_supplier(
    db_session: AsyncSession, tenant_id: uuid.UUID, **overrides: Any
) -> Supplier:
    defaults: dict[str, Any] = {
        "tenant_id": tenant_id,
        "code": f"SUP-{uuid.uuid4().hex[:8]}",
        "name": f"Supplier {uuid.uuid4().hex[:8]}",
    }
    defaults.update(overrides)
    supplier = Supplier(**defaults)
    db_session.add(supplier)
    await db_session.commit()
    return supplier


class TestSupplierModel:
    async def test_creates_with_default_status_and_zero_balances(
        self, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        supplier = await _make_supplier(db_session, tenant_id)
        await db_session.refresh(supplier)
        assert supplier.status == SupplierStatus.ACTIVE
        assert supplier.opening_balance == 0
        assert supplier.outstanding_amount == 0
        assert supplier.credit_days == 0
        assert supplier.deleted_at is None

    async def test_duplicate_code_within_tenant_is_rejected(
        self, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await _make_supplier(db_session, tenant_id, code="SUP-DUP")
        with pytest.raises(IntegrityError):
            await _make_supplier(db_session, tenant_id, code="SUP-DUP")

    async def test_same_code_allowed_across_different_tenants(
        self, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        other_tenant = Tenant(name="Other Tenant", slug=f"other-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()

        await _make_supplier(db_session, tenant_id, code="SUP-SHARED")
        # Should not raise - the unique index is scoped per tenant_id.
        await _make_supplier(db_session, other_tenant.id, code="SUP-SHARED")

    async def test_duplicate_name_case_insensitive_within_tenant_is_rejected(
        self, db_session: AsyncSession, tenant_id: uuid.UUID
    ) -> None:
        await _make_supplier(db_session, tenant_id, name="Coastal Fish Suppliers")
        with pytest.raises(IntegrityError):
            await _make_supplier(db_session, tenant_id, name="COASTAL FISH SUPPLIERS")
