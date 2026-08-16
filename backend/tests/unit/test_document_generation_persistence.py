"""Unit tests for DocumentRecordService.generate_store_and_record() (Sprint
12 Session 7: Document Generation -> Document Center Integration) - the
single generic render -> store -> record -> return mechanism every business
document-download endpoint now calls. Uses DocumentType.INVOICE with a
hand-built DocumentData (not app.modules.invoices' own builder - this test
exercises the generic mechanism, not any business module) against the real
InvoiceDocumentRenderer, which registers itself on the shared DocumentRegistry
as a side effect of `app.main:app` being imported by conftest.py."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.document_engine.document_models import DocumentData, DocumentParty, DocumentTotals
from app.core.document_engine.document_types import DocumentType
from app.core.document_engine.filename import build_document_filename
from app.core.document_engine.storage import (
    LocalStorageService,
    StorageService,
    build_document_storage_key,
)
from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import hash_password
from app.modules.documents.constants import PartyType, SourceType
from app.modules.documents.repository import DocumentRecordRepository
from app.modules.documents.service import DocumentRecordService


async def _make_tenant(db_session: AsyncSession) -> Tenant:
    tenant = Tenant(
        name="Doc Persistence Tenant", slug=f"doc-persistence-tenant-{uuid.uuid4().hex[:8]}"
    )
    db_session.add(tenant)
    await db_session.commit()
    return tenant


async def _make_user(db_session: AsyncSession, tenant_id: uuid.UUID) -> User:
    user = User(
        tenant_id=tenant_id,
        email=f"user-{uuid.uuid4().hex[:8]}@fisherp.local",
        username=f"user-{uuid.uuid4().hex[:8]}",
        password_hash=hash_password("Whatever@123"),
        full_name="Persistence Test User",
        status=AccountStatus.ACTIVE,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user


def _document_data(*, document_number: str) -> DocumentData:
    return DocumentData(
        document_type=DocumentType.INVOICE,
        document_number=document_number,
        document_date=date(2026, 8, 15),
        title="Test Invoice",
        tenant_name="Test Tenant",
        party=DocumentParty(name="Test Customer"),
        totals=DocumentTotals(subtotal=Decimal("100.00"), total=Decimal("100.00")),
        generated_at=datetime(2026, 8, 15, 4, 0, tzinfo=UTC),
        generated_by="Test User",
    )


class _AlwaysFailsToSaveStorage(StorageService):
    """A StorageService double whose save() always raises - used to
    verify that a storage failure never creates a DocumentRecord."""

    def save(self, storage_key: str, content: bytes, *, content_type: str):  # type: ignore[no-untyped-def]
        raise RuntimeError("storage backend unavailable")

    def load(self, storage_key: str) -> bytes:
        raise NotImplementedError

    def delete(self, storage_key: str) -> None:
        raise NotImplementedError

    def exists(self, storage_key: str) -> bool:
        return False

    def url(self, storage_key: str) -> str | None:
        return None


class TestGenerateStoreAndRecord:
    async def test_renders_exactly_once_and_returns_the_same_bytes_that_were_stored(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id)
        storage = LocalStorageService(root=tmp_path)
        service = DocumentRecordService(db_session, storage=storage)
        data = _document_data(document_number="INV/2026-27/00001")

        result = await service.generate_store_and_record(
            data,
            tenant_id=tenant.id,
            party_type=PartyType.CUSTOMER,
            party_id=uuid.uuid4(),
            party_name="Test Customer",
            generated_by=user.id,
        )

        assert result.content.startswith(b"%PDF-")
        assert result.content_type == "application/pdf"

        expected_filename = build_document_filename(
            DocumentType.INVOICE, data.document_number, extension="pdf"
        )
        assert result.file_name == expected_filename

        expected_storage_key = build_document_storage_key(
            str(tenant.id), DocumentType.INVOICE, expected_filename
        )
        assert storage.load(expected_storage_key) == result.content

    async def test_creates_a_document_record_with_correct_metadata(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id)
        storage = LocalStorageService(root=tmp_path)
        service = DocumentRecordService(db_session, storage=storage)
        data = _document_data(document_number="INV/2026-27/00002")
        party_id = uuid.uuid4()
        source_id = uuid.uuid4()

        result = await service.generate_store_and_record(
            data,
            tenant_id=tenant.id,
            party_type=PartyType.CUSTOMER,
            party_id=party_id,
            party_name="ABC Sea Food",
            generated_by=user.id,
            source_type=SourceType.INVOICE,
            source_id=source_id,
        )

        repo = DocumentRecordRepository(db_session)
        records, total = await repo.search(
            tenant.id,
            q=data.document_number,
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
        record = records[0]
        assert record.document_type == DocumentType.INVOICE.value
        assert record.document_number == "INV/2026-27/00002"
        assert record.party_type == PartyType.CUSTOMER.value
        assert record.party_id == party_id
        assert record.party_name == "ABC Sea Food"
        assert record.source_type == SourceType.INVOICE.value
        assert record.source_id == source_id
        assert record.generated_by == user.id
        assert record.file_name == result.file_name
        assert record.file_extension == "pdf"
        assert record.content_type == "application/pdf"
        assert record.file_size == len(result.content)
        expected_storage_key = build_document_storage_key(
            str(tenant.id), DocumentType.INVOICE, result.file_name
        )
        assert record.storage_key == expected_storage_key

    async def test_no_source_metadata_is_allowed(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Sprint 12 Session 8: source_type/source_id are optional -
        omitting them (the default) must still create a valid record,
        the same backward-compatible shape every Session 6/7 record has."""
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id)
        service = DocumentRecordService(db_session, storage=LocalStorageService(root=tmp_path))
        data = _document_data(document_number="INV/2026-27/00003a")

        await service.generate_store_and_record(
            data,
            tenant_id=tenant.id,
            party_type=PartyType.CUSTOMER,
            party_id=uuid.uuid4(),
            party_name="Test Customer",
            generated_by=user.id,
        )

        repo = DocumentRecordRepository(db_session)
        records, total = await repo.search(
            tenant.id,
            q=data.document_number,
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

    async def test_no_party_is_allowed(self, db_session: AsyncSession, tmp_path: Path) -> None:
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id)
        service = DocumentRecordService(db_session, storage=LocalStorageService(root=tmp_path))
        data = _document_data(document_number="INV/2026-27/00003")

        result = await service.generate_store_and_record(
            data,
            tenant_id=tenant.id,
            party_type=None,
            party_id=None,
            party_name=None,
            generated_by=user.id,
        )
        assert result.content.startswith(b"%PDF-")

    async def test_storage_failure_creates_no_document_record(
        self, db_session: AsyncSession
    ) -> None:
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id)
        service = DocumentRecordService(db_session, storage=_AlwaysFailsToSaveStorage())
        data = _document_data(document_number="INV/2026-27/00004")

        with pytest.raises(RuntimeError):
            await service.generate_store_and_record(
                data,
                tenant_id=tenant.id,
                party_type=PartyType.CUSTOMER,
                party_id=uuid.uuid4(),
                party_name="Test Customer",
                generated_by=user.id,
            )

        repo = DocumentRecordRepository(db_session)
        _, total = await repo.search(
            tenant.id,
            q=data.document_number,
            document_type=None,
            party_type=None,
            party_id=None,
            from_date=None,
            to_date=None,
            sort="-generated_at",
            page=1,
            page_size=20,
        )
        assert total == 0

    async def test_record_creation_failure_deletes_the_just_saved_file(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """generated_by references a nonexistent user - the DocumentRecord
        insert violates the FK constraint on commit, so
        record_generated_document() raises IntegrityError. The file was
        already written by storage.save() before that point; compensation
        must delete it rather than leave an orphaned stored file with no
        DocumentRecord pointing at it."""
        tenant = await _make_tenant(db_session)
        tenant_id = tenant.id  # captured before the rollback below expires `tenant`
        storage = LocalStorageService(root=tmp_path)
        service = DocumentRecordService(db_session, storage=storage)
        data = _document_data(document_number="INV/2026-27/00005")
        nonexistent_user_id = uuid.uuid4()

        with pytest.raises(IntegrityError):
            await service.generate_store_and_record(
                data,
                tenant_id=tenant_id,
                party_type=PartyType.CUSTOMER,
                party_id=uuid.uuid4(),
                party_name="Test Customer",
                generated_by=nonexistent_user_id,
            )

        expected_filename = build_document_filename(
            DocumentType.INVOICE, data.document_number, extension="pdf"
        )
        expected_storage_key = build_document_storage_key(
            str(tenant_id), DocumentType.INVOICE, expected_filename
        )
        assert storage.exists(expected_storage_key) is False

        # The session must still be usable afterward - the compensating
        # rollback inside record_generated_document() must have run.
        repo = DocumentRecordRepository(db_session)
        _, total = await repo.search(
            tenant_id,
            q=data.document_number,
            document_type=None,
            party_type=None,
            party_id=None,
            from_date=None,
            to_date=None,
            sort="-generated_at",
            page=1,
            page_size=20,
        )
        assert total == 0

    async def test_repeated_generation_creates_separate_records(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id)
        service = DocumentRecordService(db_session, storage=LocalStorageService(root=tmp_path))
        data = _document_data(document_number="INV/2026-27/00006")

        first = await service.generate_store_and_record(
            data,
            tenant_id=tenant.id,
            party_type=PartyType.CUSTOMER,
            party_id=uuid.uuid4(),
            party_name="Test Customer",
            generated_by=user.id,
        )
        second = await service.generate_store_and_record(
            data,
            tenant_id=tenant.id,
            party_type=PartyType.CUSTOMER,
            party_id=uuid.uuid4(),
            party_name="Test Customer",
            generated_by=user.id,
        )

        # Same document_number -> the same deterministic filename, but the
        # renderer embeds its own real creation timestamp (ReportLab's PDF
        # metadata), so the two byte streams are not expected to be
        # byte-identical - only the DocumentRecord/filename identity matters
        # here, not a byte-for-byte render cache.
        assert first.file_name == second.file_name

        repo = DocumentRecordRepository(db_session)
        records, total = await repo.search(
            tenant.id,
            q=data.document_number,
            document_type=None,
            party_type=None,
            party_id=None,
            from_date=None,
            to_date=None,
            sort="-generated_at",
            page=1,
            page_size=20,
        )
        assert total == 2
        assert records[0].id != records[1].id
        assert all(r.document_number == "INV/2026-27/00006" for r in records)
