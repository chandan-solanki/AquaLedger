"""Unit tests for app.modules.reports.statement_builder (TASKS.md Sprint
11 Session 5 Phase C) - pure DTO-to-DTO transformation, no database, no
calculation. Constructs real CustomerLedgerResponse/SupplierLedgerResponse/
CompanyResponse/SupplierResponse objects directly from the existing
Pydantic schemas and asserts the resulting ReportExportData is correct.
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.common.schemas import PaginationMeta
from app.modules.companies.schemas import CompanyResponse
from app.modules.reports.schemas import (
    CustomerLedgerCustomer,
    CustomerLedgerEntry,
    CustomerLedgerResponse,
    CustomerLedgerSummary,
    SupplierLedgerEntry,
    SupplierLedgerResponse,
    SupplierLedgerSummary,
    SupplierLedgerSupplier,
)
from app.modules.reports.statement_builder import (
    build_customer_statement_export_data,
    build_supplier_statement_export_data,
)
from app.modules.suppliers.schemas import SupplierResponse

_PAGINATION = PaginationMeta(
    total_records=1, total_pages=1, current_page=1, page_size=20, has_next=False, has_previous=False
)
_GENERATED_BY = "admin@fisherp.test"
_TENANT_NAME = "Konkan Traders"


def _make_company(**overrides: object) -> CompanyResponse:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "code": "CO-0001",
        "name": "Konkan Seafoods",
        "legal_name": None,
        "gstin": "27AAAAA0000A1Z5",
        "pan": None,
        "address_line1": "123 Harbor Road",
        "address_line2": None,
        "city": "Ratnagiri",
        "state": "Maharashtra",
        "state_code": "27",
        "pincode": "415612",
        "country": "India",
        "phone": "9876543210",
        "alt_phone": None,
        "email": None,
        "contact_person": None,
        "company_type": "customer",
        "credit_limit": Decimal("0"),
        "credit_days": 0,
        "opening_balance": Decimal("0"),
        "opening_balance_date": None,
        "opening_balance_type": "debit",
        "outstanding_amount": Decimal("0"),
        "status": "active",
        "notes": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return CompanyResponse(**defaults)


def _make_supplier(**overrides: object) -> SupplierResponse:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "code": "SUP-001",
        "name": "Coastal Fish Suppliers",
        "legal_name": None,
        "gstin": "27BBBBB0000B1Z5",
        "phone": "9998887770",
        "email": None,
        "address": "45 Fisherman Colony, Malvan",
        "city": "Malvan",
        "state": "Maharashtra",
        "country": "India",
        "contact_person": None,
        "credit_days": 15,
        "opening_balance": Decimal("0"),
        "outstanding_amount": Decimal("0"),
        "status": "active",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return SupplierResponse(**defaults)


def _make_customer_ledger(**overrides: object) -> CustomerLedgerResponse:
    defaults: dict[str, object] = {
        "customer": CustomerLedgerCustomer(id=uuid.uuid4(), name="Konkan Seafoods", code="CO-0001"),
        "summary": CustomerLedgerSummary(
            opening_balance=Decimal("100.00"),
            total_debit=Decimal("200.00"),
            total_credit=Decimal("50.00"),
            closing_balance=Decimal("250.00"),
            invoice_count=2,
            payment_count=1,
        ),
        "entries": [
            CustomerLedgerEntry(
                transaction_date=date(2026, 7, 1),
                reference_number="INV-1",
                transaction_type="invoice",
                description="Sales Invoice",
                debit=Decimal("200.00"),
                credit=Decimal("0.00"),
                running_balance=Decimal("300.00"),
            ),
            CustomerLedgerEntry(
                transaction_date=date(2026, 7, 15),
                reference_number="PAY-1",
                transaction_type="payment",
                description="Payment Received",
                debit=Decimal("0.00"),
                credit=Decimal("50.00"),
                running_balance=Decimal("250.00"),
            ),
        ],
        "pagination": _PAGINATION,
    }
    defaults.update(overrides)
    return CustomerLedgerResponse(**defaults)


def _make_supplier_ledger(**overrides: object) -> SupplierLedgerResponse:
    defaults: dict[str, object] = {
        "supplier": SupplierLedgerSupplier(
            id=uuid.uuid4(), name="Coastal Fish Suppliers", code="SUP-001"
        ),
        "summary": SupplierLedgerSummary(
            opening_balance=Decimal("0.00"),
            total_debit=Decimal("100.00"),
            total_credit=Decimal("50.00"),
            closing_balance=Decimal("50.00"),
            purchase_bill_count=1,
            supplier_payment_count=1,
        ),
        "entries": [
            SupplierLedgerEntry(
                transaction_date=date(2026, 7, 1),
                reference_number="PB-1",
                transaction_type="purchase_bill",
                description="Purchase Bill",
                debit=Decimal("100.00"),
                credit=Decimal("0.00"),
                running_balance=Decimal("100.00"),
            )
        ],
        "pagination": _PAGINATION,
    }
    defaults.update(overrides)
    return SupplierLedgerResponse(**defaults)


class TestBuildCustomerStatementExportData:
    def test_title_and_subtitle(self) -> None:
        data = build_customer_statement_export_data(
            _make_customer_ledger(),
            _make_company(),
            generated_by=_GENERATED_BY,
            tenant_name=_TENANT_NAME,
        )
        assert data.title == "Customer Statement"
        assert data.subtitle == "Konkan Seafoods (CO-0001)"

    def test_columns_exclude_transaction_type(self) -> None:
        data = build_customer_statement_export_data(
            _make_customer_ledger(),
            _make_company(),
            generated_by=_GENERATED_BY,
            tenant_name=_TENANT_NAME,
        )
        keys = [column.key for column in data.columns]
        assert keys == [
            "transaction_date",
            "reference_number",
            "description",
            "debit",
            "credit",
            "running_balance",
        ]
        assert "transaction_type" not in keys

    def test_rows_preserve_running_balance_in_order(self) -> None:
        data = build_customer_statement_export_data(
            _make_customer_ledger(),
            _make_company(),
            generated_by=_GENERATED_BY,
            tenant_name=_TENANT_NAME,
        )
        assert [row.data["running_balance"] for row in data.rows] == [
            Decimal("300.00"),
            Decimal("250.00"),
        ]
        assert [row.data["reference_number"] for row in data.rows] == ["INV-1", "PAY-1"]

    def test_summary_carries_opening_and_closing_balance_unchanged(self) -> None:
        ledger = _make_customer_ledger()
        data = build_customer_statement_export_data(
            ledger, _make_company(), generated_by=_GENERATED_BY, tenant_name=_TENANT_NAME
        )
        summary_by_label = {item.label: item.value for item in data.summary}
        assert summary_by_label["Opening Balance"] == ledger.summary.opening_balance
        assert summary_by_label["Total Debit"] == ledger.summary.total_debit
        assert summary_by_label["Total Credit"] == ledger.summary.total_credit
        assert summary_by_label["Closing Balance"] == ledger.summary.closing_balance

    def test_filters_include_name_code_address_phone_gst_and_period(self) -> None:
        data = build_customer_statement_export_data(
            _make_customer_ledger(),
            _make_company(),
            generated_by=_GENERATED_BY,
            tenant_name=_TENANT_NAME,
            from_date=date(2026, 7, 1),
            to_date=date(2026, 7, 31),
        )
        filters_by_label = {f.label: f.value for f in data.filters}
        assert filters_by_label["Customer Name"] == "Konkan Seafoods"
        assert filters_by_label["Customer Code"] == "CO-0001"
        assert (
            filters_by_label["Address"] == "123 Harbor Road, Ratnagiri, Maharashtra 415612, India"
        )
        assert filters_by_label["Phone"] == "9876543210"
        assert filters_by_label["GST Number"] == "27AAAAA0000A1Z5"
        assert filters_by_label["Statement Period"] == "2026-07-01 to 2026-07-31"

    def test_statement_period_defaults_to_all_time(self) -> None:
        data = build_customer_statement_export_data(
            _make_customer_ledger(),
            _make_company(),
            generated_by=_GENERATED_BY,
            tenant_name=_TENANT_NAME,
        )
        filters_by_label = {f.label: f.value for f in data.filters}
        assert filters_by_label["Statement Period"] == "All Time"

    def test_address_and_gst_omitted_when_not_available(self) -> None:
        company = _make_company(
            address_line1=None,
            address_line2=None,
            city=None,
            state=None,
            pincode=None,
            country=None,
            gstin=None,
            phone=None,
        )
        data = build_customer_statement_export_data(
            _make_customer_ledger(), company, generated_by=_GENERATED_BY, tenant_name=_TENANT_NAME
        )
        labels = {f.label for f in data.filters}
        assert "Address" not in labels
        assert "GST Number" not in labels
        assert "Phone" not in labels

    def test_footer_is_the_system_generated_note(self) -> None:
        data = build_customer_statement_export_data(
            _make_customer_ledger(),
            _make_company(),
            generated_by=_GENERATED_BY,
            tenant_name=_TENANT_NAME,
        )
        assert data.footer == "This is a system generated statement."

    def test_generated_by_and_tenant_name_passed_through(self) -> None:
        data = build_customer_statement_export_data(
            _make_customer_ledger(),
            _make_company(),
            generated_by=_GENERATED_BY,
            tenant_name=_TENANT_NAME,
        )
        assert data.generated_by == _GENERATED_BY
        assert data.tenant_name == _TENANT_NAME

    def test_zero_entries_still_produces_valid_export_data(self) -> None:
        ledger = _make_customer_ledger(entries=[])
        data = build_customer_statement_export_data(
            ledger, _make_company(), generated_by=_GENERATED_BY, tenant_name=_TENANT_NAME
        )
        assert data.rows == []


class TestBuildSupplierStatementExportData:
    def test_title_and_subtitle(self) -> None:
        data = build_supplier_statement_export_data(
            _make_supplier_ledger(),
            _make_supplier(),
            generated_by=_GENERATED_BY,
            tenant_name=_TENANT_NAME,
        )
        assert data.title == "Supplier Statement"
        assert data.subtitle == "Coastal Fish Suppliers (SUP-001)"

    def test_columns_exclude_transaction_type(self) -> None:
        data = build_supplier_statement_export_data(
            _make_supplier_ledger(),
            _make_supplier(),
            generated_by=_GENERATED_BY,
            tenant_name=_TENANT_NAME,
        )
        keys = [column.key for column in data.columns]
        assert "transaction_type" not in keys

    def test_rows_preserve_running_balance(self) -> None:
        data = build_supplier_statement_export_data(
            _make_supplier_ledger(),
            _make_supplier(),
            generated_by=_GENERATED_BY,
            tenant_name=_TENANT_NAME,
        )
        assert data.rows[0].data["running_balance"] == Decimal("100.00")

    def test_summary_carries_opening_and_closing_balance_unchanged(self) -> None:
        ledger = _make_supplier_ledger()
        data = build_supplier_statement_export_data(
            ledger, _make_supplier(), generated_by=_GENERATED_BY, tenant_name=_TENANT_NAME
        )
        summary_by_label = {item.label: item.value for item in data.summary}
        assert summary_by_label["Opening Balance"] == ledger.summary.opening_balance
        assert summary_by_label["Closing Balance"] == ledger.summary.closing_balance

    def test_uses_suppliers_own_single_address_field(self) -> None:
        data = build_supplier_statement_export_data(
            _make_supplier_ledger(),
            _make_supplier(address="45 Fisherman Colony, Malvan"),
            generated_by=_GENERATED_BY,
            tenant_name=_TENANT_NAME,
        )
        filters_by_label = {f.label: f.value for f in data.filters}
        assert filters_by_label["Address"] == "45 Fisherman Colony, Malvan"

    def test_filters_use_supplier_labels_not_customer_labels(self) -> None:
        data = build_supplier_statement_export_data(
            _make_supplier_ledger(),
            _make_supplier(),
            generated_by=_GENERATED_BY,
            tenant_name=_TENANT_NAME,
        )
        labels = {f.label for f in data.filters}
        assert "Supplier Name" in labels
        assert "Supplier Code" in labels
        assert "Customer Name" not in labels

    def test_footer_is_the_system_generated_note(self) -> None:
        data = build_supplier_statement_export_data(
            _make_supplier_ledger(),
            _make_supplier(),
            generated_by=_GENERATED_BY,
            tenant_name=_TENANT_NAME,
        )
        assert data.footer == "This is a system generated statement."

    def test_gst_omitted_when_not_available(self) -> None:
        data = build_supplier_statement_export_data(
            _make_supplier_ledger(),
            _make_supplier(gstin=None),
            generated_by=_GENERATED_BY,
            tenant_name=_TENANT_NAME,
        )
        labels = {f.label for f in data.filters}
        assert "GST Number" not in labels
