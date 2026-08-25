"""Unit tests for app.modules.documents.service.DocumentRecordService
(Sprint 12 Session 6: Document Center foundation). Uses a `tmp_path`-rooted
LocalStorageService so file reads/writes never touch the real configured
storage root."""

import threading
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.document_engine.document_models import DocumentData, RenderedDocument
from app.core.document_engine.document_service import DocumentService
from app.core.document_engine.document_types import DocumentType
from app.core.document_engine.storage import LocalStorageService
from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import hash_password
from app.modules.documents.constants import PartyType
from app.modules.documents.exceptions import DocumentFileMissingError, DocumentRecordNotFoundError
from app.modules.documents.schemas import DocumentListParams, DocumentRecordCreate
from app.modules.documents.service import DocumentRecordService

_DOCUMENT_DATA = DocumentData(
    document_type=DocumentType.INVOICE,
    document_number="INV-000001",
    document_date=date(2026, 8, 15),
    title="Tax Invoice",
    tenant_name="Konkan Traders",
    generated_at=datetime(2026, 8, 15, tzinfo=UTC),
    generated_by="admin@fisherp.test",
)


async def _make_tenant(db_session: AsyncSession) -> Tenant:
    tenant = Tenant(name="Doc Service Tenant", slug=f"doc-service-tenant-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    await db_session.commit()
    return tenant


async def _make_user(db_session: AsyncSession, tenant_id: uuid.UUID, *, full_name: str) -> User:
    user = User(
        tenant_id=tenant_id,
        email=f"user-{uuid.uuid4().hex[:8]}@fisherp.local",
        username=f"user-{uuid.uuid4().hex[:8]}",
        password_hash=hash_password("Whatever@123"),
        full_name=full_name,
        status=AccountStatus.ACTIVE,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user


class TestRecordGeneratedDocument:
    async def test_creates_a_record_and_resolves_the_generated_by_name(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id, full_name="Priya Admin")
        service = DocumentRecordService(db_session, storage=LocalStorageService(root=tmp_path))

        response = await service.record_generated_document(
            DocumentRecordCreate(
                tenant_id=tenant.id,
                document_type=DocumentType.INVOICE,
                document_number="INV/2026-27/00001",
                party_type=PartyType.CUSTOMER,
                party_id=uuid.uuid4(),
                party_name="ABC Sea Food",
                file_name="Invoice_INV2026-2700001.pdf",
                file_extension="pdf",
                content_type="application/pdf",
                storage_key="irrelevant-for-this-test/Invoice_INV2026-2700001.pdf",
                file_size=1024,
                generated_by=user.id,
            )
        )

        assert response.document_type is DocumentType.INVOICE
        assert response.document_number == "INV/2026-27/00001"
        assert response.party_name == "ABC Sea Food"
        assert response.generated_by == user.id
        assert response.generated_by_name == "Priya Admin"
        assert response.file_size == 1024


class TestListDocuments:
    async def test_only_returns_records_for_the_given_tenant(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant_a = await _make_tenant(db_session)
        tenant_b = await _make_tenant(db_session)
        user_a = await _make_user(db_session, tenant_a.id, full_name="User A")
        user_b = await _make_user(db_session, tenant_b.id, full_name="User B")
        service = DocumentRecordService(db_session, storage=LocalStorageService(root=tmp_path))

        for tenant, user in ((tenant_a, user_a), (tenant_b, user_b)):
            await service.record_generated_document(
                DocumentRecordCreate(
                    tenant_id=tenant.id,
                    document_type=DocumentType.INVOICE,
                    document_number="INV/2026-27/00001",
                    file_name="Invoice_INV2026-2700001.pdf",
                    file_extension="pdf",
                    content_type="application/pdf",
                    storage_key=f"{tenant.id}/documents/invoice/Invoice_INV2026-2700001.pdf",
                    file_size=1024,
                    generated_by=user.id,
                )
            )

        result = await service.list_documents(tenant_id=tenant_a.id, params=DocumentListParams())
        assert result.meta.total_records == 1
        assert all(item.document_number for item in result.data)


class TestDownload:
    async def test_returns_the_stored_bytes_and_metadata(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id, full_name="Downloader")
        storage = LocalStorageService(root=tmp_path)
        storage_key = f"{tenant.id}/documents/invoice/Invoice_INV2026-2700001.pdf"
        storage.save(storage_key, b"%PDF-1.4 fake invoice bytes", content_type="application/pdf")
        service = DocumentRecordService(db_session, storage=storage)

        record = await service.record_generated_document(
            DocumentRecordCreate(
                tenant_id=tenant.id,
                document_type=DocumentType.INVOICE,
                document_number="INV/2026-27/00001",
                file_name="Invoice_INV2026-2700001.pdf",
                file_extension="pdf",
                content_type="application/pdf",
                storage_key=storage_key,
                file_size=27,
                generated_by=user.id,
            )
        )

        download = await service.download(record.id, tenant_id=tenant.id)
        assert download.content == b"%PDF-1.4 fake invoice bytes"
        assert download.content_type == "application/pdf"
        assert download.file_name == "Invoice_INV2026-2700001.pdf"

    async def test_raises_document_file_missing_when_storage_has_no_file(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id, full_name="Downloader")
        service = DocumentRecordService(db_session, storage=LocalStorageService(root=tmp_path))

        record = await service.record_generated_document(
            DocumentRecordCreate(
                tenant_id=tenant.id,
                document_type=DocumentType.INVOICE,
                document_number="INV/2026-27/00002",
                file_name="Invoice_INV2026-2700002.pdf",
                file_extension="pdf",
                content_type="application/pdf",
                storage_key=f"{tenant.id}/documents/invoice/never-actually-saved.pdf",
                file_size=27,
                generated_by=user.id,
            )
        )

        with pytest.raises(DocumentFileMissingError):
            await service.download(record.id, tenant_id=tenant.id)

    async def test_raises_document_record_not_found_for_an_unknown_id(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session)
        service = DocumentRecordService(db_session, storage=LocalStorageService(root=tmp_path))

        with pytest.raises(DocumentRecordNotFoundError):
            await service.download(uuid.uuid4(), tenant_id=tenant.id)

    async def test_raises_document_record_not_found_for_another_tenants_record(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant_a = await _make_tenant(db_session)
        tenant_b = await _make_tenant(db_session)
        user_b = await _make_user(db_session, tenant_b.id, full_name="User B")
        service = DocumentRecordService(db_session, storage=LocalStorageService(root=tmp_path))

        record = await service.record_generated_document(
            DocumentRecordCreate(
                tenant_id=tenant_b.id,
                document_type=DocumentType.INVOICE,
                document_number="INV/2026-27/00003",
                file_name="Invoice_INV2026-2700003.pdf",
                file_extension="pdf",
                content_type="application/pdf",
                storage_key=f"{tenant_b.id}/documents/invoice/Invoice_INV2026-2700003.pdf",
                file_size=27,
                generated_by=user_b.id,
            )
        )

        with pytest.raises(DocumentRecordNotFoundError):
            await service.download(record.id, tenant_id=tenant_a.id)


class TestGenerateStoreAndRecordThreadingBoundary:
    """Sprint 18 Session 2: `DocumentService.generate()` is a synchronous,
    CPU-bound ReportLab render - `generate_store_and_record` now runs it
    via `asyncio.to_thread` so it genuinely executes off the event loop's
    own thread, not merely behind an awaitable that still runs inline.
    These tests prove real delegation (by comparing thread identity, not
    by mocking `asyncio.to_thread` itself) and that a renderer failure
    still propagates cleanly with no partial state."""

    async def test_renders_off_the_event_loop_thread(
        self, monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id, full_name="Renderer Tester")
        service = DocumentRecordService(db_session, storage=LocalStorageService(root=tmp_path))

        event_loop_thread_id = threading.get_ident()
        render_thread_ids: list[int] = []

        def fake_generate(
            self: DocumentService, _document_type: str, _data: DocumentData
        ) -> RenderedDocument:
            render_thread_ids.append(threading.get_ident())
            return RenderedDocument(
                content=b"%PDF-fake", content_type="application/pdf", file_extension="pdf"
            )

        monkeypatch.setattr(DocumentService, "generate", fake_generate)

        generated = await service.generate_store_and_record(
            _DOCUMENT_DATA,
            tenant_id=tenant.id,
            party_type=None,
            party_id=None,
            party_name=None,
            generated_by=user.id,
        )

        assert generated.content == b"%PDF-fake"
        assert len(render_thread_ids) == 1
        assert render_thread_ids[0] != event_loop_thread_id

    async def test_a_renderer_failure_propagates_without_saving_or_recording_anything(
        self, monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session)
        user = await _make_user(db_session, tenant.id, full_name="Renderer Tester")
        service = DocumentRecordService(db_session, storage=LocalStorageService(root=tmp_path))

        def fake_generate_raises(
            self: DocumentService, _document_type: str, _data: DocumentData
        ) -> RenderedDocument:
            raise RuntimeError("renderer blew up")

        monkeypatch.setattr(DocumentService, "generate", fake_generate_raises)

        with pytest.raises(RuntimeError, match="renderer blew up"):
            await service.generate_store_and_record(
                _DOCUMENT_DATA,
                tenant_id=tenant.id,
                party_type=None,
                party_id=None,
                party_name=None,
                generated_by=user.id,
            )

        # No DocumentRecord must exist for a document that was never
        # actually rendered - the failure must not be silently converted
        # into a false success, nor leave a dangling record.
        result = await service.list_documents(tenant_id=tenant.id, params=DocumentListParams())
        assert result.meta.total_records == 0
