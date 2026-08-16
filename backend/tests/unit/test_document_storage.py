from pathlib import Path

import pytest

from app.core.document_engine.document_types import DocumentType
from app.core.document_engine.exceptions import DocumentNotFoundError, InvalidStorageKeyError
from app.core.document_engine.storage import (
    DocumentFile,
    LocalStorageService,
    build_document_storage_key,
)


class TestBuildDocumentStorageKey:
    def test_builds_a_tenant_scoped_key(self) -> None:
        key = build_document_storage_key("tenant-1", DocumentType.INVOICE, "Invoice_INV-1.pdf")
        assert key == "tenant-1/documents/invoice/Invoice_INV-1.pdf"

    def test_different_tenants_never_share_a_key_for_the_same_filename(self) -> None:
        key_a = build_document_storage_key("tenant-a", DocumentType.INVOICE, "Invoice_INV-1.pdf")
        key_b = build_document_storage_key("tenant-b", DocumentType.INVOICE, "Invoice_INV-1.pdf")
        assert key_a != key_b
        assert key_a.split("/")[0] == "tenant-a"
        assert key_b.split("/")[0] == "tenant-b"

    def test_rejects_empty_tenant_id(self) -> None:
        with pytest.raises(InvalidStorageKeyError):
            build_document_storage_key("", DocumentType.INVOICE, "Invoice_INV-1.pdf")

    def test_rejects_tenant_id_containing_a_path_separator(self) -> None:
        with pytest.raises(InvalidStorageKeyError):
            build_document_storage_key("../evil", DocumentType.INVOICE, "Invoice_INV-1.pdf")


class TestLocalStorageService:
    def test_save_then_load_round_trips_the_content(self, tmp_path: Path) -> None:
        service = LocalStorageService(root=tmp_path)
        key = "tenant-1/documents/invoice/Invoice_INV-1.pdf"

        document_file = service.save(key, b"%PDF-1.4 fake", content_type="application/pdf")

        assert isinstance(document_file, DocumentFile)
        assert document_file.storage_key == key
        assert document_file.size == len(b"%PDF-1.4 fake")
        assert document_file.content_type == "application/pdf"
        assert service.load(key) == b"%PDF-1.4 fake"

    def test_save_creates_intermediate_directories(self, tmp_path: Path) -> None:
        service = LocalStorageService(root=tmp_path)
        key = "tenant-1/documents/purchase_order/PO-1.pdf"

        service.save(key, b"content", content_type="application/pdf")

        assert (tmp_path / "tenant-1" / "documents" / "purchase_order" / "PO-1.pdf").is_file()

    def test_exists_is_true_after_save_and_false_before(self, tmp_path: Path) -> None:
        service = LocalStorageService(root=tmp_path)
        key = "tenant-1/documents/invoice/Invoice_INV-1.pdf"

        assert service.exists(key) is False
        service.save(key, b"content", content_type="application/pdf")
        assert service.exists(key) is True

    def test_load_missing_key_raises_document_not_found(self, tmp_path: Path) -> None:
        service = LocalStorageService(root=tmp_path)
        with pytest.raises(DocumentNotFoundError):
            service.load("tenant-1/documents/invoice/does-not-exist.pdf")

    def test_delete_removes_the_saved_file(self, tmp_path: Path) -> None:
        service = LocalStorageService(root=tmp_path)
        key = "tenant-1/documents/invoice/Invoice_INV-1.pdf"
        service.save(key, b"content", content_type="application/pdf")

        service.delete(key)

        assert service.exists(key) is False

    def test_delete_on_a_missing_key_does_not_raise(self, tmp_path: Path) -> None:
        service = LocalStorageService(root=tmp_path)
        service.delete("tenant-1/documents/invoice/never-existed.pdf")

    def test_url_returns_none_for_local_storage(self, tmp_path: Path) -> None:
        service = LocalStorageService(root=tmp_path)
        key = "tenant-1/documents/invoice/Invoice_INV-1.pdf"
        service.save(key, b"content", content_type="application/pdf")
        assert service.url(key) is None

    @pytest.mark.parametrize(
        "malicious_key",
        [
            "../../secret.txt",
            "tenant-1/../../secret.txt",
            "tenant-1/documents/invoice/../../../secret.txt",
            "/etc/passwd",
            "C:\\Windows\\win.ini",
            "",
        ],
    )
    def test_path_traversal_and_unsafe_keys_are_rejected(
        self, tmp_path: Path, malicious_key: str
    ) -> None:
        service = LocalStorageService(root=tmp_path)
        with pytest.raises(InvalidStorageKeyError):
            service.save(malicious_key, b"content", content_type="text/plain")

    def test_path_traversal_cannot_escape_root_even_via_load(self, tmp_path: Path) -> None:
        secret = tmp_path.parent / "secret.txt"
        secret.write_text("do not read me")
        service = LocalStorageService(root=tmp_path)
        with pytest.raises(InvalidStorageKeyError):
            service.load("../secret.txt")
