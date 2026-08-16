"""Unit tests for app.modules.documents.repository.DocumentRecordRepository
(Sprint 12 Session 6: Document Center foundation). Exercises real
tenant-scoped queries against the test database via the shared
`db_session` fixture (rolled back after every test, see conftest.py) -
"unit" here means "below the HTTP layer", not "no database"."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import hash_password
from app.modules.documents.constants import PartyType, SourceType
from app.modules.documents.models import DocumentRecord
from app.modules.documents.repository import DocumentRecordRepository


async def _make_tenant(db_session: AsyncSession) -> Tenant:
    tenant = Tenant(name="Doc Repo Tenant", slug=f"doc-repo-tenant-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    await db_session.commit()
    return tenant


async def _make_user(db_session: AsyncSession, tenant_id: uuid.UUID) -> User:
    user = User(
        tenant_id=tenant_id,
        email=f"user-{uuid.uuid4().hex[:8]}@fisherp.local",
        username=f"user-{uuid.uuid4().hex[:8]}",
        password_hash=hash_password("Whatever@123"),
        full_name="Repo Test User",
        status=AccountStatus.ACTIVE,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user


async def _add_record(
    db_session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    generated_by: uuid.UUID,
    document_type: str = "invoice",
    document_number: str = "INV/2026-27/00001",
    party_type: PartyType | None = PartyType.CUSTOMER,
    party_id: uuid.UUID | None = None,
    party_name: str | None = "ABC Sea Food",
    source_type: SourceType | None = None,
    source_id: uuid.UUID | None = None,
    file_name: str = "Invoice_INV2026-2700001.pdf",
    generated_at: datetime | None = None,
) -> DocumentRecord:
    record = DocumentRecord(
        tenant_id=tenant_id,
        document_type=document_type,
        document_number=document_number,
        party_type=party_type.value if party_type else None,
        party_id=party_id or (uuid.uuid4() if party_type else None),
        party_name=party_name,
        source_type=source_type.value if source_type else None,
        source_id=source_id,
        file_name=file_name,
        file_extension="pdf",
        content_type="application/pdf",
        storage_key=f"{tenant_id}/documents/{document_type}/{file_name}",
        file_size=1024,
        generated_by=generated_by,
    )
    db_session.add(record)
    await db_session.commit()
    if generated_at is not None:
        record.generated_at = generated_at
        await db_session.commit()
    return record


class TestTenantIsolation:
    async def test_a_search_never_returns_another_tenants_records(
        self, db_session: AsyncSession
    ) -> None:
        tenant_a = await _make_tenant(db_session)
        tenant_b = await _make_tenant(db_session)
        user_a = await _make_user(db_session, tenant_a.id)
        user_b = await _make_user(db_session, tenant_b.id)
        await _add_record(db_session, tenant_id=tenant_a.id, generated_by=user_a.id)
        await _add_record(db_session, tenant_id=tenant_b.id, generated_by=user_b.id)

        repo = DocumentRecordRepository(db_session)
        records, total = await repo.search(
            tenant_a.id,
            q=None,
            document_type=None,
            party_type=None,
            party_id=None,
            from_date=None,
            to_date=None,
            sort="-generated_at",
            page=1,
            page_size=20,
        )

        assert total == 1
        assert all(r.tenant_id == tenant_a.id for r in records)

    async def test_get_by_id_is_none_for_a_record_in_another_tenant(
        self, db_session: AsyncSession
    ) -> None:
        tenant_a = await _make_tenant(db_session)
        tenant_b = await _make_tenant(db_session)
        user_b = await _make_user(db_session, tenant_b.id)
        record = await _add_record(db_session, tenant_id=tenant_b.id, generated_by=user_b.id)

        repo = DocumentRecordRepository(db_session)
        result = await repo.get_by_id(record.id, tenant_a.id)
        assert result is None


class TestFilters:
    async def test_document_type_filter(self, db_session: AsyncSession) -> None:
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id)
        await _add_record(
            db_session, tenant_id=tenant.id, generated_by=user.id, document_type="invoice"
        )
        await _add_record(
            db_session, tenant_id=tenant.id, generated_by=user.id, document_type="purchase_bill"
        )

        repo = DocumentRecordRepository(db_session)
        records, total = await repo.search(
            tenant.id,
            q=None,
            document_type="purchase_bill",
            party_type=None,
            party_id=None,
            from_date=None,
            to_date=None,
            sort="-generated_at",
            page=1,
            page_size=20,
        )
        assert total == 1
        assert records[0].document_type == "purchase_bill"

    async def test_party_filter(self, db_session: AsyncSession) -> None:
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id)
        target_party_id = uuid.uuid4()
        await _add_record(
            db_session,
            tenant_id=tenant.id,
            generated_by=user.id,
            party_type=PartyType.CUSTOMER,
            party_id=target_party_id,
        )
        await _add_record(
            db_session, tenant_id=tenant.id, generated_by=user.id, party_type=PartyType.SUPPLIER
        )

        repo = DocumentRecordRepository(db_session)
        records, total = await repo.search(
            tenant.id,
            q=None,
            document_type=None,
            party_type=PartyType.CUSTOMER,
            party_id=target_party_id,
            from_date=None,
            to_date=None,
            sort="-generated_at",
            page=1,
            page_size=20,
        )
        assert total == 1
        assert records[0].party_id == target_party_id

    async def test_search_matches_document_number(self, db_session: AsyncSession) -> None:
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id)
        await _add_record(
            db_session,
            tenant_id=tenant.id,
            generated_by=user.id,
            document_number="INV/2026-27/00042",
        )
        await _add_record(
            db_session,
            tenant_id=tenant.id,
            generated_by=user.id,
            document_number="INV/2026-27/00099",
        )

        repo = DocumentRecordRepository(db_session)
        records, total = await repo.search(
            tenant.id,
            q="00042",
            document_type=None,
            party_type=None,
            party_id=None,
            from_date=None,
            to_date=None,
            sort="-generated_at",
            page=1,
            page_size=20,
        )
        assert total == 1
        assert records[0].document_number == "INV/2026-27/00042"

    async def test_search_matches_party_name(self, db_session: AsyncSession) -> None:
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id)
        await _add_record(
            db_session, tenant_id=tenant.id, generated_by=user.id, party_name="Konkan Seafoods"
        )
        await _add_record(
            db_session, tenant_id=tenant.id, generated_by=user.id, party_name="Malvan Traders"
        )

        repo = DocumentRecordRepository(db_session)
        _, total = await repo.search(
            tenant.id,
            q="konkan",
            document_type=None,
            party_type=None,
            party_id=None,
            from_date=None,
            to_date=None,
            sort="-generated_at",
            page=1,
            page_size=20,
        )
        assert total == 1

    async def test_date_range_filter(self, db_session: AsyncSession) -> None:
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id)
        await _add_record(
            db_session,
            tenant_id=tenant.id,
            generated_by=user.id,
            generated_at=datetime(2026, 7, 1, tzinfo=UTC),
        )
        await _add_record(
            db_session,
            tenant_id=tenant.id,
            generated_by=user.id,
            generated_at=datetime(2026, 8, 1, tzinfo=UTC),
        )

        repo = DocumentRecordRepository(db_session)
        _, total = await repo.search(
            tenant.id,
            q=None,
            document_type=None,
            party_type=None,
            party_id=None,
            from_date=datetime(2026, 7, 15).date(),
            to_date=datetime(2026, 8, 15).date(),
            sort="-generated_at",
            page=1,
            page_size=20,
        )
        assert total == 1

    async def test_empty_result_when_nothing_matches(self, db_session: AsyncSession) -> None:
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id)
        await _add_record(db_session, tenant_id=tenant.id, generated_by=user.id)

        repo = DocumentRecordRepository(db_session)
        records, total = await repo.search(
            tenant.id,
            q="no-such-thing-exists",
            document_type=None,
            party_type=None,
            party_id=None,
            from_date=None,
            to_date=None,
            sort="-generated_at",
            page=1,
            page_size=20,
        )
        assert records == []
        assert total == 0


class TestSourceFieldsPersistence:
    """Sprint 12 Session 8: source_type/source_id round-trip through
    search() unchanged - no new filter was added for them, but the ORM
    columns must persist and come back correctly."""

    async def test_source_fields_round_trip(self, db_session: AsyncSession) -> None:
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id)
        source_id = uuid.uuid4()
        await _add_record(
            db_session,
            tenant_id=tenant.id,
            generated_by=user.id,
            source_type=SourceType.PAYMENT,
            source_id=source_id,
        )

        repo = DocumentRecordRepository(db_session)
        records, total = await repo.search(
            tenant.id,
            q=None,
            document_type=None,
            party_type=None,
            party_id=None,
            from_date=None,
            to_date=None,
            sort="-generated_at",
            page=1,
            page_size=20,
        )
        assert total == 1
        assert records[0].source_type == SourceType.PAYMENT.value
        assert records[0].source_id == source_id

    async def test_null_source_fields_are_valid(self, db_session: AsyncSession) -> None:
        """A record created before source_type/source_id existed (or by
        a caller that doesn't yet supply them) has both as NULL - it
        must still be returned normally, not excluded or erroring."""
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id)
        await _add_record(db_session, tenant_id=tenant.id, generated_by=user.id)

        repo = DocumentRecordRepository(db_session)
        records, total = await repo.search(
            tenant.id,
            q=None,
            document_type=None,
            party_type=None,
            party_id=None,
            from_date=None,
            to_date=None,
            sort="-generated_at",
            page=1,
            page_size=20,
        )
        assert total == 1
        assert records[0].source_type is None
        assert records[0].source_id is None


class TestOrderingAndPagination:
    async def test_ordered_by_generated_at_descending_by_default(
        self, db_session: AsyncSession
    ) -> None:
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id)
        older = await _add_record(
            db_session,
            tenant_id=tenant.id,
            generated_by=user.id,
            document_number="OLD-1",
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        newer = await _add_record(
            db_session,
            tenant_id=tenant.id,
            generated_by=user.id,
            document_number="NEW-1",
            generated_at=datetime(2026, 6, 1, tzinfo=UTC),
        )

        repo = DocumentRecordRepository(db_session)
        records, _ = await repo.search(
            tenant.id,
            q=None,
            document_type=None,
            party_type=None,
            party_id=None,
            from_date=None,
            to_date=None,
            sort="-generated_at",
            page=1,
            page_size=20,
        )
        assert [r.id for r in records] == [newer.id, older.id]

    async def test_pagination_slices_correctly(self, db_session: AsyncSession) -> None:
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id)
        for i in range(5):
            await _add_record(
                db_session,
                tenant_id=tenant.id,
                generated_by=user.id,
                document_number=f"PAGE-{i}",
                generated_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=i),
            )

        repo = DocumentRecordRepository(db_session)
        page_one, total = await repo.search(
            tenant.id,
            q=None,
            document_type=None,
            party_type=None,
            party_id=None,
            from_date=None,
            to_date=None,
            sort="document_number",
            page=1,
            page_size=2,
        )
        page_two, _ = await repo.search(
            tenant.id,
            q=None,
            document_type=None,
            party_type=None,
            party_id=None,
            from_date=None,
            to_date=None,
            sort="document_number",
            page=2,
            page_size=2,
        )

        assert total == 5
        assert len(page_one) == 2
        assert len(page_two) == 2
        assert {r.document_number for r in page_one}.isdisjoint(
            {r.document_number for r in page_two}
        )
