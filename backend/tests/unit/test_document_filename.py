import pytest

from app.core.document_engine.document_types import DocumentType
from app.core.document_engine.filename import build_document_filename


class TestBuildDocumentFilename:
    def test_invoice_example_from_the_spec(self) -> None:
        filename = build_document_filename(DocumentType.INVOICE, "INV-000001", extension="pdf")
        assert filename == "Invoice_INV-000001.pdf"

    def test_purchase_bill_example_from_the_spec(self) -> None:
        filename = build_document_filename(DocumentType.PURCHASE_BILL, "PB-000021", extension="pdf")
        assert filename == "Purchase_Bill_PB-000021.pdf"

    def test_customer_payment_receipt_example_from_the_spec(self) -> None:
        filename = build_document_filename(
            DocumentType.CUSTOMER_PAYMENT_RECEIPT, "RCP-000055", extension="pdf"
        )
        assert filename == "Customer_Payment_Receipt_RCP-000055.pdf"

    def test_supplier_payment_receipt_example_from_the_spec(self) -> None:
        filename = build_document_filename(
            DocumentType.SUPPLIER_PAYMENT_RECEIPT, "SPR-000031", extension="pdf"
        )
        assert filename == "Supplier_Payment_Receipt_SPR-000031.pdf"

    def test_purchase_order_example_from_the_spec(self) -> None:
        filename = build_document_filename(
            DocumentType.PURCHASE_ORDER, "PO-000021", extension="pdf"
        )
        assert filename == "Purchase_Order_PO-000021.pdf"

    def test_delivery_challan_example_from_the_spec(self) -> None:
        filename = build_document_filename(
            DocumentType.DELIVERY_CHALLAN, "DC-000044", extension="pdf"
        )
        assert filename == "Delivery_Challan_DC-000044.pdf"

    def test_illegal_filename_characters_are_stripped(self) -> None:
        filename = build_document_filename(
            DocumentType.INVOICE, 'INV/000<1>:"weird"', extension="pdf"
        )
        assert not any(char in filename for char in '<>:"/\\|?*')

    def test_path_traversal_attempt_never_escapes_the_filename(self) -> None:
        filename = build_document_filename(DocumentType.INVOICE, "../../secret", extension="pdf")
        assert "/" not in filename
        assert "\\" not in filename

    def test_repeated_whitespace_collapses_to_a_single_underscore(self) -> None:
        filename = build_document_filename(DocumentType.INVOICE, "INV   000001", extension="pdf")
        assert filename == "Invoice_INV_000001.pdf"

    def test_extension_is_appended_verbatim_and_separately(self) -> None:
        assert build_document_filename(
            DocumentType.INVOICE, "INV-000001", extension="pdf"
        ).endswith(".pdf")
        assert build_document_filename(
            DocumentType.INVOICE, "INV-000001", extension="html"
        ).endswith(".html")

    def test_naming_is_deterministic_no_random_component(self) -> None:
        first = build_document_filename(DocumentType.INVOICE, "INV-000001", extension="pdf")
        second = build_document_filename(DocumentType.INVOICE, "INV-000001", extension="pdf")
        assert first == second

    def test_document_number_preserved_when_already_clean(self) -> None:
        filename = build_document_filename(DocumentType.INVOICE, "INV-000001", extension="pdf")
        assert "INV-000001" in filename

    def test_document_number_that_sanitizes_to_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="document_number"):
            build_document_filename(DocumentType.INVOICE, "///", extension="pdf")
