"""Unit tests for app.modules.delivery_challans.document_builder (Sprint 12
Session 16) - pure DTO -> DocumentData mapping. No database, no HTTP - every
response DTO below is hand-built, mirroring
test_purchase_order_document_builder.py's own style."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.core.document_engine.document_models import DocumentData
from app.core.document_engine.document_types import DocumentType
from app.modules.companies.constants import CompanyStatus, CompanyType
from app.modules.companies.schemas import CompanyResponse
from app.modules.delivery_challans.constants import DeliveryChallanStatus
from app.modules.delivery_challans.document_builder import build_delivery_challan_document_data
from app.modules.delivery_challans.schemas import (
    DeliveryChallanItemResponse,
    DeliveryChallanResponse,
)
from app.modules.fish.schemas import FishResponse
from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.schemas import InvoiceItemResponse, InvoiceResponse

_TENANT_ID = uuid.uuid4()
_COMPANY_ID = uuid.uuid4()
_INVOICE_ID = uuid.uuid4()
_CHALLAN_ID = uuid.uuid4()
_FISH_ID = uuid.uuid4()
_INVOICE_ITEM_ID = uuid.uuid4()
_NOW = datetime(2026, 8, 15, 10, 30, tzinfo=UTC)


def _make_challan(**overrides: object) -> DeliveryChallanResponse:
    defaults: dict[str, object] = {
        "id": _CHALLAN_ID,
        "tenant_id": _TENANT_ID,
        "invoice_id": _INVOICE_ID,
        "challan_number": "DC/2026-27/00001",
        "challan_date": date(2026, 8, 15),
        "status": DeliveryChallanStatus.DISPATCHED,
        "remarks": None,
        "dispatched_at": _NOW,
        "delivered_at": None,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    defaults.update(overrides)
    return DeliveryChallanResponse(**defaults)


def _make_item(**overrides: object) -> DeliveryChallanItemResponse:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "tenant_id": _TENANT_ID,
        "delivery_challan_id": _CHALLAN_ID,
        "invoice_item_id": _INVOICE_ITEM_ID,
        "line_number": 1,
        "quantity": Decimal("40.000"),
        "unit": "KG",
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    defaults.update(overrides)
    return DeliveryChallanItemResponse(**defaults)


def _make_invoice(**overrides: object) -> InvoiceResponse:
    defaults: dict[str, object] = {
        "id": _INVOICE_ID,
        "tenant_id": _TENANT_ID,
        "company_id": _COMPANY_ID,
        "invoice_number": "INV/2026-27/00001",
        "invoice_date": date(2026, 8, 1),
        "due_date": date(2026, 8, 16),
        "status": InvoiceStatus.ISSUED,
        "subtotal": Decimal("22500.00"),
        "discount_amount": Decimal("0.00"),
        "taxable_amount": Decimal("22500.00"),
        "tax_amount": Decimal("1125.00"),
        "transport_charge": Decimal("0.00"),
        "other_charge": Decimal("0.00"),
        "round_off": Decimal("0.00"),
        "total_amount": Decimal("23625.00"),
        "paid_amount": Decimal("10000.00"),
        "balance_amount": Decimal("13625.00"),
        "remarks": None,
        "issued_at": _NOW,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    defaults.update(overrides)
    return InvoiceResponse(**defaults)


def _make_invoice_item(**overrides: object) -> InvoiceItemResponse:
    defaults: dict[str, object] = {
        "id": _INVOICE_ITEM_ID,
        "tenant_id": _TENANT_ID,
        "invoice_id": _INVOICE_ID,
        "line_number": 1,
        "fish_id": _FISH_ID,
        "trip_catch_id": uuid.uuid4(),
        "description": "Grade A",
        "quantity": Decimal("100.000"),
        "unit": "KG",
        "rate": Decimal("450.0000"),
        "discount_percent": Decimal("0.00"),
        "discount_amount": Decimal("0.00"),
        "taxable_amount": Decimal("45000.00"),
        "tax_rate": Decimal("5.00"),
        "tax_amount": Decimal("2250.00"),
        "line_total": Decimal("47250.00"),
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    defaults.update(overrides)
    return InvoiceItemResponse(**defaults)


def _make_fish(**overrides: object) -> FishResponse:
    defaults: dict[str, object] = {
        "id": _FISH_ID,
        "tenant_id": _TENANT_ID,
        "code": "FISH-001",
        "name": "Pomfret",
        "local_name": "Paplet",
        "scientific_name": "Pampus argenteus",
        "category": "Whitefish",
        "unit": "kg",
        "default_purchase_rate": Decimal("450.0000"),
        "default_sale_rate": Decimal("550.0000"),
        "hsn_code": "0302",
        "description": None,
        "is_active": True,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    defaults.update(overrides)
    return FishResponse(**defaults)


def _make_company(**overrides: object) -> CompanyResponse:
    defaults: dict[str, object] = {
        "id": _COMPANY_ID,
        "tenant_id": _TENANT_ID,
        "code": "CUST-001",
        "name": "Ocean Fresh Traders",
        "legal_name": "Ocean Fresh Traders Pvt Ltd",
        "gstin": "27ABCDE1234F1Z5",
        "pan": "ABCDE1234F",
        "address_line1": "12 Harbour Road",
        "address_line2": None,
        "city": "Mumbai",
        "state": "Maharashtra",
        "state_code": "27",
        "pincode": "400001",
        "country": "India",
        "phone": "9876543210",
        "alt_phone": None,
        "email": "contact@oceanfresh.example",
        "contact_person": "Ravi Kumar",
        "company_type": CompanyType.CUSTOMER,
        "credit_limit": Decimal("500000.00"),
        "credit_days": 30,
        "opening_balance": Decimal("0.00"),
        "opening_balance_date": None,
        "opening_balance_type": None,
        "outstanding_amount": Decimal("0.00"),
        "status": CompanyStatus.ACTIVE,
        "notes": None,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    defaults.update(overrides)
    return CompanyResponse(**defaults)


def _build(
    *,
    challan: DeliveryChallanResponse | None = None,
    items: list[DeliveryChallanItemResponse] | None = None,
    invoice: InvoiceResponse | None = None,
    invoice_item: InvoiceItemResponse | None = None,
    fish: FishResponse | None = None,
    previously_delivered: Decimal = Decimal("0"),
    company: CompanyResponse | None = None,
) -> DocumentData:
    resolved_items = items if items is not None else [_make_item()]
    resolved_invoice_item = invoice_item or _make_invoice_item()
    resolved_fish = fish or _make_fish()
    return build_delivery_challan_document_data(
        challan or _make_challan(),
        resolved_items,
        invoice or _make_invoice(),
        {resolved_invoice_item.id: resolved_invoice_item},
        {resolved_fish.id: resolved_fish},
        {item.id: previously_delivered for item in resolved_items},
        company or _make_company(),
        tenant_name="Konkan Traders",
        generated_by="admin@fisherp.test",
    )


class TestBuildDeliveryChallanDocumentData:
    def test_document_type_is_delivery_challan(self) -> None:
        data = _build()
        assert data.document_type == DocumentType.DELIVERY_CHALLAN

    def test_document_number_is_the_actual_challan_number(self) -> None:
        data = _build(challan=_make_challan(challan_number="DC/2026-27/00042"))
        assert data.document_number == "DC/2026-27/00042"

    def test_document_date_is_the_actual_challan_date(self) -> None:
        data = _build(challan=_make_challan(challan_date=date(2026, 1, 5)))
        assert data.document_date == date(2026, 1, 5)

    def test_title_is_delivery_challan(self) -> None:
        data = _build()
        assert data.title == "Delivery Challan"

    def test_customer_mapping(self) -> None:
        data = _build()
        assert data.party is not None
        assert data.party.name == "Ocean Fresh Traders"
        assert data.party.code == "CUST-001"
        assert data.party.phone == "9876543210"
        assert data.party.email == "contact@oceanfresh.example"
        assert data.party.tax_id == "27ABCDE1234F1Z5"
        assert data.party.address == "12 Harbour Road, Mumbai, Maharashtra 400001, India"

    def test_customer_optional_fields_omitted_when_unavailable(self) -> None:
        company = _make_company(
            phone=None,
            email=None,
            gstin=None,
            address_line1=None,
            city=None,
            state=None,
            country=None,
        )
        data = _build(company=company)
        assert data.party is not None
        assert data.party.phone is None
        assert data.party.email is None
        assert data.party.tax_id is None

    def test_item_description_combines_fish_name_and_description(self) -> None:
        data = _build(invoice_item=_make_invoice_item(description="Grade A"))
        assert len(data.line_items) == 1
        assert data.line_items[0].description == "Pomfret - Grade A"

    def test_item_description_falls_back_to_fish_name_when_no_description(self) -> None:
        data = _build(invoice_item=_make_invoice_item(description=None))
        assert data.line_items[0].description == "Pomfret"

    def test_item_quantity_and_unit_mapping(self) -> None:
        item = _make_item(quantity=Decimal("40.000"), unit="KG")
        data = _build(items=[item])
        line = data.line_items[0]
        assert line.quantity == Decimal("40.000")
        assert line.unit == "KG"

    def test_invoiced_quantity_travels_in_line_metadata(self) -> None:
        invoice_item = _make_invoice_item(quantity=Decimal("100.000"))
        data = _build(invoice_item=invoice_item)
        assert data.line_items[0].metadata["invoiced_quantity"] == Decimal("100.000")

    def test_previously_delivered_quantity_travels_in_line_metadata(self) -> None:
        data = _build(previously_delivered=Decimal("30.000"))
        assert data.line_items[0].metadata["previously_delivered_quantity"] == Decimal("30.000")

    def test_multi_item_mapping_preserves_order(self) -> None:
        invoice_item_a = _make_invoice_item(id=uuid.uuid4(), description="A")
        invoice_item_b = _make_invoice_item(id=uuid.uuid4(), description="B")
        item_a = _make_item(
            line_number=1, invoice_item_id=invoice_item_a.id, quantity=Decimal("10.000")
        )
        item_b = _make_item(
            line_number=2, invoice_item_id=invoice_item_b.id, quantity=Decimal("20.000")
        )
        data = build_delivery_challan_document_data(
            _make_challan(),
            [item_a, item_b],
            _make_invoice(),
            {invoice_item_a.id: invoice_item_a, invoice_item_b.id: invoice_item_b},
            {_FISH_ID: _make_fish()},
            {item_a.id: Decimal("0"), item_b.id: Decimal("0")},
            _make_company(),
            tenant_name="Konkan Traders",
            generated_by="admin@fisherp.test",
        )
        assert len(data.line_items) == 2
        assert data.line_items[0].quantity == Decimal("10.000")
        assert data.line_items[1].quantity == Decimal("20.000")

    def test_totals_are_never_set(self) -> None:
        """Hard business rule: a delivery challan is not a financial
        document, so DocumentTotals must never be populated at all."""
        data = _build()
        assert data.totals is None

    def test_no_calculation_inside_builder(self) -> None:
        """Passing an internally-inconsistent previously-delivered figure
        must round-trip unchanged - the builder must never recompute or
        re-validate the delivered-quantity aggregation, only copy what the
        service already computed."""
        data = _build(previously_delivered=Decimal("999.000"))
        assert data.line_items[0].metadata["previously_delivered_quantity"] == Decimal("999.000")

    def test_notes_maps_from_remarks_when_present(self) -> None:
        data = _build(challan=_make_challan(remarks="Handle with care"))
        assert data.notes == "Handle with care"

    def test_notes_omitted_when_no_remarks(self) -> None:
        data = _build(challan=_make_challan(remarks=None))
        assert data.notes is None

    def test_tenant_name_and_generated_by_are_passed_through(self) -> None:
        item = _make_item()
        data = build_delivery_challan_document_data(
            _make_challan(),
            [item],
            _make_invoice(),
            {_INVOICE_ITEM_ID: _make_invoice_item()},
            {_FISH_ID: _make_fish()},
            {item.id: Decimal("0")},
            _make_company(),
            tenant_name="Konkan Traders",
            generated_by="Ravi Kumar",
        )
        assert data.tenant_name == "Konkan Traders"
        assert data.generated_by == "Ravi Kumar"

    def test_status_is_carried_in_metadata(self) -> None:
        data = _build(challan=_make_challan(status=DeliveryChallanStatus.DELIVERED))
        assert data.metadata["status"] == "delivered"

    def test_invoice_number_and_date_are_carried_in_metadata(self) -> None:
        data = _build(
            invoice=_make_invoice(invoice_number="INV/2026-27/00099", invoice_date=date(2026, 8, 1))
        )
        assert data.metadata["invoice_number"] == "INV/2026-27/00099"
        assert data.metadata["invoice_date"] == date(2026, 8, 1)

    def test_dispatched_and_delivered_at_are_carried_in_metadata(self) -> None:
        data = _build(challan=_make_challan(dispatched_at=_NOW, delivered_at=None))
        assert data.metadata["dispatched_at"] == _NOW
        assert data.metadata["delivered_at"] is None

    def test_raises_when_challan_number_is_missing(self) -> None:
        with pytest.raises(ValueError, match="challan_number"):
            _build(challan=_make_challan(challan_number=None))
