"""Unit tests for app.modules.purchase_orders.document_builder (Sprint 12
Session 11) - pure DTO -> DocumentData mapping. No database, no HTTP -
every PurchaseOrderResponse/PurchaseOrderItemResponse/SupplierResponse
below is hand-built, mirroring test_purchase_bill_document_builder.py's
own style."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.core.document_engine.document_types import DocumentType
from app.modules.purchase_orders.constants import PurchaseOrderStatus
from app.modules.purchase_orders.document_builder import build_purchase_order_document_data
from app.modules.purchase_orders.schemas import PurchaseOrderItemResponse, PurchaseOrderResponse
from app.modules.suppliers.constants import SupplierStatus
from app.modules.suppliers.schemas import SupplierResponse

_TENANT_ID = uuid.uuid4()
_SUPPLIER_ID = uuid.uuid4()
_ORDER_ID = uuid.uuid4()
_NOW = datetime(2026, 8, 15, 10, 30, tzinfo=UTC)


def _make_order(**overrides: object) -> PurchaseOrderResponse:
    defaults: dict[str, object] = {
        "id": _ORDER_ID,
        "tenant_id": _TENANT_ID,
        "supplier_id": _SUPPLIER_ID,
        "po_number": "PO/2026-27/00001",
        "order_date": date(2026, 8, 15),
        "expected_delivery_date": date(2026, 8, 25),
        "status": PurchaseOrderStatus.CONFIRMED,
        "subtotal": Decimal("22500.00"),
        "discount_amount": Decimal("0.00"),
        "taxable_amount": Decimal("22500.00"),
        "tax_amount": Decimal("1125.00"),
        "transport_charge": Decimal("0.00"),
        "other_charge": Decimal("0.00"),
        "round_off": Decimal("0.00"),
        "total_amount": Decimal("23625.00"),
        "remarks": None,
        "confirmed_at": _NOW,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    defaults.update(overrides)
    return PurchaseOrderResponse(**defaults)


def _make_item(**overrides: object) -> PurchaseOrderItemResponse:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "tenant_id": _TENANT_ID,
        "purchase_order_id": _ORDER_ID,
        "line_number": 1,
        "description": "Pomfret - Grade A",
        "quantity": Decimal("50.000"),
        "unit": "KG",
        "rate": Decimal("450.0000"),
        "discount_percent": Decimal("0.00"),
        "discount_amount": Decimal("0.00"),
        "taxable_amount": Decimal("22500.00"),
        "tax_rate": Decimal("5.00"),
        "tax_amount": Decimal("1125.00"),
        "line_total": Decimal("23625.00"),
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    defaults.update(overrides)
    return PurchaseOrderItemResponse(**defaults)


def _make_supplier(**overrides: object) -> SupplierResponse:
    defaults: dict[str, object] = {
        "id": _SUPPLIER_ID,
        "tenant_id": _TENANT_ID,
        "code": "SUP-001",
        "name": "Coastal Fish Suppliers",
        "legal_name": "Coastal Fish Suppliers Pvt Ltd",
        "gstin": "27ABCDE1234F1Z5",
        "phone": "9876543210",
        "email": "contact@coastalfish.example",
        "address": "12 Harbour Road",
        "city": "Mumbai",
        "state": "Maharashtra",
        "country": "India",
        "contact_person": "Ravi Kumar",
        "credit_days": 30,
        "opening_balance": Decimal("0.00"),
        "outstanding_amount": Decimal("0.00"),
        "status": SupplierStatus.ACTIVE,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    defaults.update(overrides)
    return SupplierResponse(**defaults)


class TestBuildPurchaseOrderDocumentData:
    def test_document_type_is_purchase_order(self) -> None:
        data = build_purchase_order_document_data(
            _make_order(),
            [_make_item()],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.document_type == DocumentType.PURCHASE_ORDER

    def test_document_number_is_the_actual_po_number(self) -> None:
        data = build_purchase_order_document_data(
            _make_order(po_number="PO/2026-27/00042"),
            [_make_item()],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.document_number == "PO/2026-27/00042"

    def test_document_date_is_the_actual_order_date(self) -> None:
        data = build_purchase_order_document_data(
            _make_order(order_date=date(2026, 1, 5)),
            [_make_item()],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.document_date == date(2026, 1, 5)

    def test_supplier_mapping(self) -> None:
        data = build_purchase_order_document_data(
            _make_order(),
            [_make_item()],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.party is not None
        assert data.party.name == "Coastal Fish Suppliers"
        assert data.party.code == "SUP-001"
        assert data.party.phone == "9876543210"
        assert data.party.email == "contact@coastalfish.example"
        assert data.party.tax_id == "27ABCDE1234F1Z5"
        assert data.party.address == "12 Harbour Road, Mumbai, Maharashtra, India"

    def test_supplier_optional_fields_omitted_when_unavailable(self) -> None:
        supplier = _make_supplier(
            phone=None, email=None, gstin=None, address=None, city=None, state=None, country=None
        )
        data = build_purchase_order_document_data(
            _make_order(),
            [_make_item()],
            supplier,
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.party is not None
        assert data.party.phone is None
        assert data.party.email is None
        assert data.party.tax_id is None
        assert data.party.address is None

    def test_single_line_item_mapping(self) -> None:
        item = _make_item(
            description="Surmai",
            quantity=Decimal("50.000"),
            unit="KG",
            rate=Decimal("450.0000"),
            tax_rate=Decimal("5.00"),
            tax_amount=Decimal("1125.00"),
            line_total=Decimal("23625.00"),
        )
        data = build_purchase_order_document_data(
            _make_order(),
            [item],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert len(data.line_items) == 1
        line = data.line_items[0]
        assert line.description == "Surmai"
        assert line.quantity == Decimal("50.000")
        assert line.unit == "KG"
        assert line.unit_price == Decimal("450.0000")
        assert line.tax_amount == Decimal("1125.00")
        assert line.line_total == Decimal("23625.00")

    def test_multi_line_item_mapping_preserves_order(self) -> None:
        item_a = _make_item(line_number=1, description="Pomfret", line_total=Decimal("100.00"))
        item_b = _make_item(line_number=2, description="Surmai", line_total=Decimal("200.00"))
        data = build_purchase_order_document_data(
            _make_order(),
            [item_a, item_b],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert len(data.line_items) == 2
        assert data.line_items[0].description == "Pomfret"
        assert data.line_items[0].line_total == Decimal("100.00")
        assert data.line_items[1].description == "Surmai"
        assert data.line_items[1].line_total == Decimal("200.00")

    def test_line_item_falls_back_to_dash_when_description_missing(self) -> None:
        """description is nullable at the DB level even though the API
        always requires it - defensive, not a normally reachable path."""
        item = _make_item(description=None)
        data = build_purchase_order_document_data(
            _make_order(),
            [item],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.line_items[0].description == "-"

    def test_totals_mapping_uses_authoritative_backend_values(self) -> None:
        order = _make_order(
            subtotal=Decimal("22500.00"),
            discount_amount=Decimal("500.00"),
            tax_amount=Decimal("1100.00"),
            round_off=Decimal("0.25"),
            total_amount=Decimal("23100.25"),
        )
        data = build_purchase_order_document_data(
            order,
            [_make_item()],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.totals is not None
        assert data.totals.subtotal == Decimal("22500.00")
        assert data.totals.discount == Decimal("500.00")
        assert data.totals.tax == Decimal("1100.00")
        assert data.totals.rounding == Decimal("0.25")
        assert data.totals.total == Decimal("23100.25")

    def test_totals_never_carry_paid_or_balance(self) -> None:
        """Hard business rule: a purchase order is not a payable document,
        so DocumentTotals.paid/balance must always stay unset, regardless
        of what totals the order itself carries."""
        data = build_purchase_order_document_data(
            _make_order(),
            [_make_item()],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.totals is not None
        assert data.totals.paid is None
        assert data.totals.balance is None

    def test_no_calculation_inside_builder(self) -> None:
        """Passing internally-inconsistent totals must round-trip
        unchanged - the builder must never recompute subtotal/tax/total
        from the line items, only copy whatever the backend already
        computed."""
        order = _make_order(
            subtotal=Decimal("999.99"),
            tax_amount=Decimal("111.11"),
            total_amount=Decimal("500.00"),
        )
        item = _make_item(line_total=Decimal("23625.00"))
        data = build_purchase_order_document_data(
            order,
            [item],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.totals is not None
        assert data.totals.subtotal == Decimal("999.99")
        assert data.totals.total == Decimal("500.00")
        assert data.line_items[0].line_total == Decimal("23625.00")

    def test_additional_charges_section_present_when_nonzero(self) -> None:
        order = _make_order(transport_charge=Decimal("250.00"), other_charge=Decimal("50.00"))
        data = build_purchase_order_document_data(
            order,
            [_make_item()],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert len(data.sections) == 1
        section = data.sections[0]
        assert section.title == "Additional Charges"
        descriptions = {line.description: line.line_total for line in section.lines}
        assert descriptions == {
            "Transport Charge": Decimal("250.00"),
            "Other Charge": Decimal("50.00"),
        }

    def test_additional_charges_section_omitted_when_zero(self) -> None:
        order = _make_order(transport_charge=Decimal("0.00"), other_charge=Decimal("0.00"))
        data = build_purchase_order_document_data(
            order,
            [_make_item()],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.sections == []

    def test_notes_maps_from_remarks_when_present(self) -> None:
        data = build_purchase_order_document_data(
            _make_order(remarks="Weekly restock"),
            [_make_item()],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.notes == "Weekly restock"

    def test_notes_omitted_when_no_remarks(self) -> None:
        data = build_purchase_order_document_data(
            _make_order(remarks=None),
            [_make_item()],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.notes is None

    def test_terms_are_never_set_since_purchase_order_model_has_no_terms_field(self) -> None:
        data = build_purchase_order_document_data(
            _make_order(),
            [_make_item()],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.terms is None

    def test_tenant_name_and_generated_by_are_passed_through(self) -> None:
        data = build_purchase_order_document_data(
            _make_order(),
            [_make_item()],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="Ravi Kumar",
        )
        assert data.tenant_name == "Konkan Traders"
        assert data.generated_by == "Ravi Kumar"

    def test_tenant_details_is_never_set_since_tenant_has_no_address_fields(self) -> None:
        data = build_purchase_order_document_data(
            _make_order(),
            [_make_item()],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.tenant_details is None

    def test_status_is_carried_in_metadata(self) -> None:
        data = build_purchase_order_document_data(
            _make_order(status=PurchaseOrderStatus.FULFILLED),
            [_make_item()],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.metadata["status"] == "fulfilled"

    def test_expected_delivery_date_is_carried_in_metadata_when_present(self) -> None:
        data = build_purchase_order_document_data(
            _make_order(expected_delivery_date=date(2026, 9, 1)),
            [_make_item()],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.metadata["expected_delivery_date"] == date(2026, 9, 1)

    def test_expected_delivery_date_is_none_when_not_set(self) -> None:
        data = build_purchase_order_document_data(
            _make_order(expected_delivery_date=None),
            [_make_item()],
            _make_supplier(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert data.metadata["expected_delivery_date"] is None

    def test_raises_when_po_number_is_missing(self) -> None:
        with pytest.raises(ValueError, match="po_number"):
            build_purchase_order_document_data(
                _make_order(po_number=None),
                [_make_item()],
                _make_supplier(),
                tenant_name="Konkan Traders",
                generated_by="admin@fisherp.test",
            )
