"""Unit tests for app.modules.documents.schemas (Sprint 12 Session 6:
Document Center foundation). Pure Pydantic validation, no DB access."""

import uuid

import pytest
from pydantic import ValidationError

from app.core.document_engine.document_types import DocumentType
from app.modules.documents.constants import PartyType, SourceType
from app.modules.documents.schemas import DocumentListParams, DocumentRecordCreate

_BASE_CREATE_KWARGS: dict[str, object] = {
    "tenant_id": uuid.uuid4(),
    "document_type": DocumentType.INVOICE,
    "document_number": "INV/2026-27/00001",
    "file_name": "Invoice_INV2026-2700001.pdf",
    "file_extension": "pdf",
    "content_type": "application/pdf",
    "storage_key": "tenant-1/documents/invoice/Invoice_INV2026-2700001.pdf",
    "file_size": 48213,
    "generated_by": uuid.uuid4(),
}


class TestDocumentRecordCreate:
    def test_accepts_a_valid_document_record_with_no_party(self) -> None:
        record = DocumentRecordCreate(**_BASE_CREATE_KWARGS)  # type: ignore[arg-type]
        assert record.document_type is DocumentType.INVOICE
        assert record.party_type is None
        assert record.party_id is None

    def test_accepts_a_valid_document_record_with_a_party(self) -> None:
        record = DocumentRecordCreate(
            **_BASE_CREATE_KWARGS,  # type: ignore[arg-type]
            party_type=PartyType.CUSTOMER,
            party_id=uuid.uuid4(),
            party_name="ABC Sea Food",
        )
        assert record.party_type is PartyType.CUSTOMER
        assert record.party_name == "ABC Sea Food"

    def test_rejects_an_unknown_document_type(self) -> None:
        kwargs = {**_BASE_CREATE_KWARGS, "document_type": "not_a_real_type"}
        with pytest.raises(ValidationError):
            DocumentRecordCreate(**kwargs)  # type: ignore[arg-type]

    def test_rejects_a_blank_document_number(self) -> None:
        kwargs = {**_BASE_CREATE_KWARGS, "document_number": ""}
        with pytest.raises(ValidationError):
            DocumentRecordCreate(**kwargs)  # type: ignore[arg-type]

    def test_rejects_a_blank_file_name(self) -> None:
        kwargs = {**_BASE_CREATE_KWARGS, "file_name": ""}
        with pytest.raises(ValidationError):
            DocumentRecordCreate(**kwargs)  # type: ignore[arg-type]

    def test_rejects_a_blank_content_type(self) -> None:
        kwargs = {**_BASE_CREATE_KWARGS, "content_type": ""}
        with pytest.raises(ValidationError):
            DocumentRecordCreate(**kwargs)  # type: ignore[arg-type]

    def test_rejects_a_zero_file_size(self) -> None:
        kwargs = {**_BASE_CREATE_KWARGS, "file_size": 0}
        with pytest.raises(ValidationError):
            DocumentRecordCreate(**kwargs)  # type: ignore[arg-type]

    def test_rejects_a_negative_file_size(self) -> None:
        kwargs = {**_BASE_CREATE_KWARGS, "file_size": -1}
        with pytest.raises(ValidationError):
            DocumentRecordCreate(**kwargs)  # type: ignore[arg-type]

    def test_rejects_party_id_without_party_type(self) -> None:
        kwargs = {**_BASE_CREATE_KWARGS, "party_id": uuid.uuid4()}
        with pytest.raises(ValidationError):
            DocumentRecordCreate(**kwargs)  # type: ignore[arg-type]

    def test_rejects_party_type_without_party_id(self) -> None:
        kwargs = {**_BASE_CREATE_KWARGS, "party_type": PartyType.SUPPLIER}
        with pytest.raises(ValidationError):
            DocumentRecordCreate(**kwargs)  # type: ignore[arg-type]

    def test_accepts_a_valid_document_record_with_source_metadata(self) -> None:
        record = DocumentRecordCreate(
            **_BASE_CREATE_KWARGS,  # type: ignore[arg-type]
            source_type=SourceType.INVOICE,
            source_id=uuid.uuid4(),
        )
        assert record.source_type is SourceType.INVOICE
        assert record.source_id is not None

    def test_accepts_a_valid_document_record_with_no_source_metadata(self) -> None:
        """Sprint 12 Session 8 added source_type/source_id as optional -
        every DocumentRecord created before this field existed (Sessions
        6-7) has neither, and that must remain a fully valid record."""
        record = DocumentRecordCreate(**_BASE_CREATE_KWARGS)  # type: ignore[arg-type]
        assert record.source_type is None
        assert record.source_id is None

    def test_rejects_an_unknown_source_type(self) -> None:
        kwargs = {
            **_BASE_CREATE_KWARGS,
            "source_type": "not_a_real_source",
            "source_id": uuid.uuid4(),
        }
        with pytest.raises(ValidationError):
            DocumentRecordCreate(**kwargs)  # type: ignore[arg-type]

    def test_rejects_source_id_without_source_type(self) -> None:
        kwargs = {**_BASE_CREATE_KWARGS, "source_id": uuid.uuid4()}
        with pytest.raises(ValidationError):
            DocumentRecordCreate(**kwargs)  # type: ignore[arg-type]

    def test_rejects_source_type_without_source_id(self) -> None:
        kwargs = {**_BASE_CREATE_KWARGS, "source_type": SourceType.PAYMENT}
        with pytest.raises(ValidationError):
            DocumentRecordCreate(**kwargs)  # type: ignore[arg-type]


class TestDocumentListParams:
    def test_defaults(self) -> None:
        params = DocumentListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort == "-generated_at"
        assert params.document_type is None

    def test_accepts_a_valid_sort_field(self) -> None:
        assert DocumentListParams(sort="document_number").sort == "document_number"
        assert DocumentListParams(sort="-generated_at").sort == "-generated_at"

    def test_rejects_an_unknown_sort_field(self) -> None:
        with pytest.raises(ValidationError):
            DocumentListParams(sort="totally_unsortable")

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            DocumentListParams(page=0)

    def test_rejects_page_size_above_the_ceiling(self) -> None:
        with pytest.raises(ValidationError):
            DocumentListParams(page_size=101)

    def test_rejects_search_longer_than_the_max_length(self) -> None:
        with pytest.raises(ValidationError):
            DocumentListParams(q="x" * 256)

    def test_accepts_an_ordered_date_range(self) -> None:
        params = DocumentListParams(from_date="2026-07-01", to_date="2026-07-31")
        assert params.from_date is not None
        assert params.to_date is not None

    def test_rejects_from_date_after_to_date(self) -> None:
        with pytest.raises(ValidationError):
            DocumentListParams(from_date="2026-07-31", to_date="2026-07-01")

    def test_accepts_a_document_type_filter(self) -> None:
        params = DocumentListParams(document_type=DocumentType.PURCHASE_BILL)
        assert params.document_type is DocumentType.PURCHASE_BILL

    def test_rejects_an_unknown_document_type_filter(self) -> None:
        with pytest.raises(ValidationError):
            DocumentListParams(document_type="not_a_real_type")
