import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.common.schemas import PaginationMeta
from app.modules.fish.constants import FishUnit
from app.modules.invoices.constants import InvoiceStatus
from app.modules.purchase.constants import PurchaseStatus
from app.modules.reports.constants import (
    EntityType,
    PaidStatus,
    ProfitabilityFilter,
    RiskLevel,
    SupplierTransactionType,
    TransactionType,
)
from app.modules.trips.constants import TripStatus


class CustomerLedgerCustomer(BaseModel):
    """Customer Information section of the Customer Ledger response
    (TASKS.md Sprint 11 Session 1)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "019f7af3-83ae-783a-b139-40a239786b30",
                "name": "Konkan Seafoods",
                "code": "CO-0001",
            }
        }
    )

    id: uuid.UUID
    name: str
    code: str


class CustomerLedgerSummary(BaseModel):
    """Ledger Summary section - always computed from the customer's full
    invoice+payment history for the requested date range, unaffected by the
    `transaction_type` filter (that filter only narrows which rows appear in
    `entries`) - see ReportsService.get_customer_ledger's docstring."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "opening_balance": "12500.00",
                "total_debit": "48250.00",
                "total_credit": "35000.00",
                "closing_balance": "25750.00",
                "invoice_count": 6,
                "payment_count": 4,
            }
        }
    )

    opening_balance: Decimal
    total_debit: Decimal
    total_credit: Decimal
    closing_balance: Decimal
    invoice_count: int
    payment_count: int


class CustomerLedgerEntry(BaseModel):
    """One row of the Ledger Entries section - one issued/partially-paid/
    paid invoice (debit) or one posted payment (credit), per the
    ACCOUNTING RULES (TASKS.md Sprint 11 Session 1). `running_balance`
    always reflects the true cumulative account balance up to and including
    this transaction, even when `transaction_type` is filtered to just this
    row's own type."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "transaction_date": "2026-07-15",
                "reference_number": "INV/2026-27/00015",
                "transaction_type": "invoice",
                "description": "Sales Invoice",
                "debit": "23875.00",
                "credit": "0.00",
                "running_balance": "36375.00",
            }
        }
    )

    transaction_date: date
    reference_number: str
    transaction_type: TransactionType
    description: str
    debit: Decimal
    credit: Decimal
    running_balance: Decimal


class CustomerLedgerResponse(BaseModel):
    """GET /reports/customer-ledger's response body - Customer Information,
    Ledger Summary, Ledger Entries and Pagination Metadata, per TASKS.md
    Sprint 11 Session 1's "LEDGER STRUCTURE"."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer": {
                    "id": "019f7af3-83ae-783a-b139-40a239786b30",
                    "name": "Konkan Seafoods",
                    "code": "CO-0001",
                },
                "summary": {
                    "opening_balance": "12500.00",
                    "total_debit": "48250.00",
                    "total_credit": "35000.00",
                    "closing_balance": "25750.00",
                    "invoice_count": 6,
                    "payment_count": 4,
                },
                "entries": [
                    {
                        "transaction_date": "2026-07-15",
                        "reference_number": "INV/2026-27/00015",
                        "transaction_type": "invoice",
                        "description": "Sales Invoice",
                        "debit": "23875.00",
                        "credit": "0.00",
                        "running_balance": "36375.00",
                    }
                ],
                "pagination": {
                    "total_records": 6,
                    "total_pages": 1,
                    "current_page": 1,
                    "page_size": 20,
                    "has_next": False,
                    "has_previous": False,
                },
            }
        }
    )

    customer: CustomerLedgerCustomer
    summary: CustomerLedgerSummary
    entries: list[CustomerLedgerEntry]
    pagination: PaginationMeta


class CustomerLedgerParams(BaseModel):
    """Query params for GET /reports/customer-ledger - bound via FastAPI's
    Depends() model support, mirroring InvoiceListParams."""

    customer_id: uuid.UUID = Field(
        description="The customer (company) whose ledger to generate - required."
    )
    from_date: date | None = Field(
        default=None, description="Inclusive lower bound on transaction_date."
    )
    to_date: date | None = Field(
        default=None, description="Inclusive upper bound on transaction_date."
    )
    transaction_type: TransactionType | None = Field(
        default=None, description="Restrict entries to invoices or payments only."
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def _check_date_range(self) -> "CustomerLedgerParams":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must not be after to_date")
        return self


class SupplierLedgerSupplier(BaseModel):
    """Supplier Information section of the Supplier Ledger response
    (TASKS.md Sprint 11 Session 2)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "019f7af3-83ae-783a-b139-40a239786b31",
                "name": "Coastal Fish Suppliers",
                "code": "SUP-001",
            }
        }
    )

    id: uuid.UUID
    name: str
    code: str


class SupplierLedgerSummary(BaseModel):
    """Ledger Summary section - always computed from the supplier's full
    purchase-bill+payment history for the requested date range, unaffected
    by the `transaction_type` filter (that filter only narrows which rows
    appear in `entries`) - see ReportsService.get_supplier_ledger's
    docstring. Mirrors CustomerLedgerSummary exactly, on the buy side."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "opening_balance": "12500.00",
                "total_debit": "48250.00",
                "total_credit": "35000.00",
                "closing_balance": "25750.00",
                "purchase_bill_count": 6,
                "supplier_payment_count": 4,
            }
        }
    )

    opening_balance: Decimal
    total_debit: Decimal
    total_credit: Decimal
    closing_balance: Decimal
    purchase_bill_count: int
    supplier_payment_count: int


class SupplierLedgerEntry(BaseModel):
    """One row of the Ledger Entries section - one posted purchase bill
    (debit) or one posted supplier payment (credit), per the ACCOUNTING
    RULES (TASKS.md Sprint 11 Session 2). `running_balance` always reflects
    the true cumulative account balance up to and including this
    transaction, even when `transaction_type` is filtered to just this
    row's own type."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "transaction_date": "2026-07-15",
                "reference_number": "PB/2026-27/00015",
                "transaction_type": "purchase_bill",
                "description": "Purchase Bill",
                "debit": "23875.00",
                "credit": "0.00",
                "running_balance": "36375.00",
            }
        }
    )

    transaction_date: date
    reference_number: str
    transaction_type: SupplierTransactionType
    description: str
    debit: Decimal
    credit: Decimal
    running_balance: Decimal


class SupplierLedgerResponse(BaseModel):
    """GET /reports/supplier-ledger's response body - Supplier Information,
    Ledger Summary, Ledger Entries and Pagination Metadata, per TASKS.md
    Sprint 11 Session 2's "LEDGER STRUCTURE". Mirrors CustomerLedgerResponse
    exactly, on the buy side."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "supplier": {
                    "id": "019f7af3-83ae-783a-b139-40a239786b31",
                    "name": "Coastal Fish Suppliers",
                    "code": "SUP-001",
                },
                "summary": {
                    "opening_balance": "12500.00",
                    "total_debit": "48250.00",
                    "total_credit": "35000.00",
                    "closing_balance": "25750.00",
                    "purchase_bill_count": 6,
                    "supplier_payment_count": 4,
                },
                "entries": [
                    {
                        "transaction_date": "2026-07-15",
                        "reference_number": "PB/2026-27/00015",
                        "transaction_type": "purchase_bill",
                        "description": "Purchase Bill",
                        "debit": "23875.00",
                        "credit": "0.00",
                        "running_balance": "36375.00",
                    }
                ],
                "pagination": {
                    "total_records": 6,
                    "total_pages": 1,
                    "current_page": 1,
                    "page_size": 20,
                    "has_next": False,
                    "has_previous": False,
                },
            }
        }
    )

    supplier: SupplierLedgerSupplier
    summary: SupplierLedgerSummary
    entries: list[SupplierLedgerEntry]
    pagination: PaginationMeta


class SupplierLedgerParams(BaseModel):
    """Query params for GET /reports/supplier-ledger - bound via FastAPI's
    Depends() model support, mirroring CustomerLedgerParams."""

    supplier_id: uuid.UUID = Field(description="The supplier whose ledger to generate - required.")
    from_date: date | None = Field(
        default=None, description="Inclusive lower bound on transaction_date."
    )
    to_date: date | None = Field(
        default=None, description="Inclusive upper bound on transaction_date."
    )
    transaction_type: SupplierTransactionType | None = Field(
        default=None, description="Restrict entries to purchase bills or supplier payments only."
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def _check_date_range(self) -> "SupplierLedgerParams":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must not be after to_date")
        return self


class SalesReportRow(BaseModel):
    """One row of the Sales Report - one issued invoice (TASKS.md Sprint 11
    Session 3: "one row = one invoice"). `invoice_id` is the drill-down key
    the frontend links to the existing Invoice Detail page with - the report
    itself has no other use for it."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "invoice_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c03",
                "invoice_number": "INV/2026-27/00015",
                "invoice_date": "2026-07-15",
                "due_date": "2026-07-30",
                "customer_name": "Konkan Seafoods",
                "invoice_amount": "23625.00",
                "paid_amount": "10000.00",
                "outstanding_amount": "13625.00",
                "status": "partially_paid",
            }
        }
    )

    invoice_id: uuid.UUID
    invoice_number: str
    invoice_date: date
    due_date: date | None
    customer_name: str
    invoice_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    status: InvoiceStatus


class SalesReportSummary(BaseModel):
    """Always computed over the FULL filtered set (every matching invoice,
    not just the current page) - the same "aggregate over filters, not over
    the page" discipline every report in this module follows."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_sales": "148250.00",
                "total_paid": "95000.00",
                "outstanding": "53250.00",
                "invoice_count": 6,
                "average_invoice": "24708.33",
                "largest_invoice": "48250.00",
            }
        }
    )

    total_sales: Decimal
    total_paid: Decimal
    outstanding: Decimal
    invoice_count: int
    average_invoice: Decimal
    largest_invoice: Decimal


class SalesReportResponse(BaseModel):
    """GET /reports/sales's response body (TASKS.md Sprint 11 Session 3)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "summary": {
                    "total_sales": "148250.00",
                    "total_paid": "95000.00",
                    "outstanding": "53250.00",
                    "invoice_count": 6,
                    "average_invoice": "24708.33",
                    "largest_invoice": "48250.00",
                },
                "rows": [
                    {
                        "invoice_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c03",
                        "invoice_number": "INV/2026-27/00015",
                        "invoice_date": "2026-07-15",
                        "due_date": "2026-07-30",
                        "customer_name": "Konkan Seafoods",
                        "invoice_amount": "23625.00",
                        "paid_amount": "10000.00",
                        "outstanding_amount": "13625.00",
                        "status": "partially_paid",
                    }
                ],
                "pagination": {
                    "total_records": 6,
                    "total_pages": 1,
                    "current_page": 1,
                    "page_size": 20,
                    "has_next": False,
                    "has_previous": False,
                },
            }
        }
    )

    summary: SalesReportSummary
    rows: list[SalesReportRow]
    pagination: PaginationMeta


class SalesReportParams(BaseModel):
    """Query params for GET /reports/sales - bound via FastAPI's Depends()
    model support. There is deliberately no `sort` field: TASKS.md's
    SORTING section for this report ("Invoice Date DESC, Invoice Number
    DESC") is a fixed, deterministic order - not a user-selectable option -
    mirroring how the Customer/Supplier Ledger's own chronological order is
    fixed, not client-configurable."""

    from_date: date | None = Field(
        default=None, description="Inclusive lower bound on invoice_date."
    )
    to_date: date | None = Field(default=None, description="Inclusive upper bound on invoice_date.")
    customer_id: uuid.UUID | None = Field(
        default=None, description="Filter by billed customer (company)."
    )
    status: InvoiceStatus | None = Field(
        default=None,
        description="Filter by invoice status. Draft invoices are always excluded "
        "regardless of this filter - the report only ever shows invoices that were "
        "issued.",
    )
    paid_status: PaidStatus | None = Field(
        default=None, description="Filter by payment progress, independent of `status`."
    )
    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across invoice_number and the billed "
        "customer's name - serves both the Invoice Number and Search filters.",
        examples=["INV-2026"],
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def _check_date_range(self) -> "SalesReportParams":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must not be after to_date")
        return self


class PurchaseReportRow(BaseModel):
    """One row of the Purchase Report - one posted purchase bill (TASKS.md
    Sprint 11 Session 3: "one row = one purchase bill"). Mirrors
    SalesReportRow exactly, on the buy side."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "bill_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c05",
                "bill_number": "PUR/2026-27/00015",
                "bill_date": "2026-07-15",
                "due_date": "2026-08-14",
                "supplier_name": "Coastal Fish Suppliers",
                "bill_amount": "23625.00",
                "paid_amount": "10000.00",
                "outstanding_amount": "13625.00",
                "status": "partially_paid",
            }
        }
    )

    bill_id: uuid.UUID
    bill_number: str
    bill_date: date
    due_date: date | None
    supplier_name: str
    bill_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    status: PurchaseStatus


class PurchaseReportSummary(BaseModel):
    """Mirrors SalesReportSummary exactly, on the buy side - always computed
    over the FULL filtered set, never just the current page."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_purchases": "148250.00",
                "total_paid": "95000.00",
                "outstanding": "53250.00",
                "bill_count": 6,
                "average_bill": "24708.33",
                "largest_bill": "48250.00",
            }
        }
    )

    total_purchases: Decimal
    total_paid: Decimal
    outstanding: Decimal
    bill_count: int
    average_bill: Decimal
    largest_bill: Decimal


class PurchaseReportResponse(BaseModel):
    """GET /reports/purchases's response body (TASKS.md Sprint 11 Session 3).
    Mirrors SalesReportResponse exactly, on the buy side."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "summary": {
                    "total_purchases": "148250.00",
                    "total_paid": "95000.00",
                    "outstanding": "53250.00",
                    "bill_count": 6,
                    "average_bill": "24708.33",
                    "largest_bill": "48250.00",
                },
                "rows": [
                    {
                        "bill_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c05",
                        "bill_number": "PUR/2026-27/00015",
                        "bill_date": "2026-07-15",
                        "due_date": "2026-08-14",
                        "supplier_name": "Coastal Fish Suppliers",
                        "bill_amount": "23625.00",
                        "paid_amount": "10000.00",
                        "outstanding_amount": "13625.00",
                        "status": "partially_paid",
                    }
                ],
                "pagination": {
                    "total_records": 6,
                    "total_pages": 1,
                    "current_page": 1,
                    "page_size": 20,
                    "has_next": False,
                    "has_previous": False,
                },
            }
        }
    )

    summary: PurchaseReportSummary
    rows: list[PurchaseReportRow]
    pagination: PaginationMeta


class PurchaseReportParams(BaseModel):
    """Query params for GET /reports/purchases - mirrors SalesReportParams
    exactly, on the buy side. No `sort` field, for the same reason:
    TASKS.md's SORTING section ("Bill Date DESC, Bill Number DESC") is a
    fixed order, not user-selectable."""

    from_date: date | None = Field(default=None, description="Inclusive lower bound on bill_date.")
    to_date: date | None = Field(default=None, description="Inclusive upper bound on bill_date.")
    supplier_id: uuid.UUID | None = Field(default=None, description="Filter by billing supplier.")
    status: PurchaseStatus | None = Field(
        default=None,
        description="Filter by purchase bill status. Draft bills are always excluded "
        "regardless of this filter - the report only ever shows bills that were posted.",
    )
    paid_status: PaidStatus | None = Field(
        default=None, description="Filter by payment progress, independent of `status`."
    )
    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across bill_number and the billing "
        "supplier's name - serves both the Bill Number and Search filters.",
        examples=["PUR-2026"],
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def _check_date_range(self) -> "PurchaseReportParams":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must not be after to_date")
        return self


class OutstandingReportRow(BaseModel):
    """One row of the Outstanding Report - one customer or one supplier
    (TASKS.md Sprint 11 Session 3 Phase B: "one row = one business entity,
    NOT one transaction"), whichever `entity_type` the request asked for.
    `entity_id`/`entity_name`/`entity_code` are generic rather than
    `customer_id`/`supplier_id` because a single response shape serves both
    tabs - the frontend already knows which tab it asked for."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_id": "019f7af3-83ae-783a-b139-40a239786b30",
                "entity_name": "Konkan Seafoods",
                "entity_code": "CO-0001",
                "outstanding_amount": "23875.00",
                "overdue_amount": "13625.00",
                "current_amount": "10250.00",
                "last_transaction_date": "2026-07-15",
                "last_payment_date": "2026-07-10",
                "pending_count": 3,
                "risk_level": "medium",
            }
        }
    )

    entity_id: uuid.UUID
    entity_name: str
    entity_code: str
    outstanding_amount: Decimal
    overdue_amount: Decimal
    current_amount: Decimal
    last_transaction_date: date | None
    last_payment_date: date | None
    pending_count: int
    risk_level: RiskLevel


class OutstandingReportSummary(BaseModel):
    """Always the full, unfiltered grand totals across every customer and
    supplier with invoice/purchase-bill history - fixed accounting KPIs
    (Accounts Receivable/Payable), never narrowed by `entity_type` or any
    row-level filter (outstanding_only/overdue_only/risk_level/q/date
    range), which only ever affect which *rows* the table shows. See
    ReportsService.get_outstanding_report's docstring."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "accounts_receivable": "148250.00",
                "accounts_payable": "62500.00",
                "net_position": "85750.00",
                "overdue_receivable": "53250.00",
                "overdue_payable": "19000.00",
                "customers_with_outstanding": 8,
                "suppliers_with_outstanding": 3,
            }
        }
    )

    accounts_receivable: Decimal
    accounts_payable: Decimal
    net_position: Decimal
    overdue_receivable: Decimal
    overdue_payable: Decimal
    customers_with_outstanding: int
    suppliers_with_outstanding: int


class OutstandingReportResponse(BaseModel):
    """GET /reports/outstanding's response body (TASKS.md Sprint 11 Session
    3 Phase B). One response shape serves both the "Customer Outstanding"
    and "Supplier Outstanding" tabs - `entity_type` echoes back which tab
    `rows` belongs to; `summary` is always the combined AR/AP picture
    regardless of `entity_type`."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_type": "customer",
                "summary": {
                    "accounts_receivable": "148250.00",
                    "accounts_payable": "62500.00",
                    "net_position": "85750.00",
                    "overdue_receivable": "53250.00",
                    "overdue_payable": "19000.00",
                    "customers_with_outstanding": 8,
                    "suppliers_with_outstanding": 3,
                },
                "rows": [
                    {
                        "entity_id": "019f7af3-83ae-783a-b139-40a239786b30",
                        "entity_name": "Konkan Seafoods",
                        "entity_code": "CO-0001",
                        "outstanding_amount": "23875.00",
                        "overdue_amount": "13625.00",
                        "current_amount": "10250.00",
                        "last_transaction_date": "2026-07-15",
                        "last_payment_date": "2026-07-10",
                        "pending_count": 3,
                        "risk_level": "medium",
                    }
                ],
                "pagination": {
                    "total_records": 8,
                    "total_pages": 1,
                    "current_page": 1,
                    "page_size": 20,
                    "has_next": False,
                    "has_previous": False,
                },
            }
        }
    )

    entity_type: EntityType
    summary: OutstandingReportSummary
    rows: list[OutstandingReportRow]
    pagination: PaginationMeta


class OutstandingReportParams(BaseModel):
    """Query params for GET /reports/outstanding - bound via FastAPI's
    Depends() model support. `entity_type` selects the "Customer
    Outstanding"/"Supplier Outstanding" tab (defaults to `customer` so a
    bare request is never a 422). `from_date`/`to_date` bound which
    invoices/purchase bills count toward each entity's totals by their
    transaction date (invoice_date/bill_date) - independent of the
    overdue/current split, which always compares each transaction's
    due_date to today. There is no `sort` field: TASKS.md's SORTING
    section ("Outstanding DESC, Then Name ASC") is a fixed order."""

    entity_type: EntityType = Field(default=EntityType.CUSTOMER)
    outstanding_only: bool = Field(
        default=False, description="Restrict rows to entities with outstanding_amount > 0."
    )
    overdue_only: bool = Field(
        default=False, description="Restrict rows to entities with overdue_amount > 0."
    )
    risk_level: RiskLevel | None = Field(default=None, description="Filter by risk_level.")
    from_date: date | None = Field(
        default=None, description="Inclusive lower bound on invoice_date/bill_date."
    )
    to_date: date | None = Field(
        default=None, description="Inclusive upper bound on invoice_date/bill_date."
    )
    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across the entity's name and code.",
        examples=["Konkan"],
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def _check_date_range(self) -> "OutstandingReportParams":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must not be after to_date")
        return self


class AgingReportRow(BaseModel):
    """One row of the Aging Report - one customer or one supplier, bucketed
    by how overdue their unpaid invoices/purchase bills are, by due_date
    (never invoice_date/bill_date - TASKS.md Sprint 11 Session 3 Phase B:
    "Use Invoice Due Date / Purchase Bill Due Date. Never Invoice Date.").
    `risk_level` is not one of the report's displayed "Columns", but is
    included so the `risk` filter has something to filter on - it is
    computed identically to OutstandingReportRow.risk_level."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_id": "019f7af3-83ae-783a-b139-40a239786b30",
                "entity_name": "Konkan Seafoods",
                "entity_code": "CO-0001",
                "current_amount": "10250.00",
                "days_1_30": "5000.00",
                "days_31_60": "8625.00",
                "days_61_90": "0.00",
                "days_90_plus": "0.00",
                "total": "23875.00",
                "risk_level": "medium",
            }
        }
    )

    entity_id: uuid.UUID
    entity_name: str
    entity_code: str
    current_amount: Decimal
    days_1_30: Decimal
    days_31_60: Decimal
    days_61_90: Decimal
    days_90_plus: Decimal
    total: Decimal
    risk_level: RiskLevel


class AgingReportSummary(BaseModel):
    """Column totals across the full filtered set (every matching row, not
    just the current page) - mirrors every other report's own summary
    discipline in this module, scoped to the requested `entity_type` (all
    field names here are generic bucket labels with no AR/AP distinction,
    unlike OutstandingReportSummary's `accounts_receivable`/
    `accounts_payable`, so there is no reason for this to span both sides
    at once)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_total": "42500.00",
                "days_1_30_total": "35000.00",
                "days_31_60_total": "48250.00",
                "days_61_90_total": "12500.00",
                "days_90_plus_total": "10000.00",
                "grand_total": "148250.00",
            }
        }
    )

    current_total: Decimal
    days_1_30_total: Decimal
    days_31_60_total: Decimal
    days_61_90_total: Decimal
    days_90_plus_total: Decimal
    grand_total: Decimal


class AgingReportResponse(BaseModel):
    """GET /reports/aging's response body (TASKS.md Sprint 11 Session 3
    Phase B). Mirrors OutstandingReportResponse's "one shape, two tabs"
    structure, except `summary` here IS scoped to `entity_type` - see
    AgingReportSummary's own docstring."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_type": "customer",
                "summary": {
                    "current_total": "42500.00",
                    "days_1_30_total": "35000.00",
                    "days_31_60_total": "48250.00",
                    "days_61_90_total": "12500.00",
                    "days_90_plus_total": "10000.00",
                    "grand_total": "148250.00",
                },
                "rows": [
                    {
                        "entity_id": "019f7af3-83ae-783a-b139-40a239786b30",
                        "entity_name": "Konkan Seafoods",
                        "entity_code": "CO-0001",
                        "current_amount": "10250.00",
                        "days_1_30": "5000.00",
                        "days_31_60": "8625.00",
                        "days_61_90": "0.00",
                        "days_90_plus": "0.00",
                        "total": "23875.00",
                        "risk_level": "medium",
                    }
                ],
                "pagination": {
                    "total_records": 8,
                    "total_pages": 1,
                    "current_page": 1,
                    "page_size": 20,
                    "has_next": False,
                    "has_previous": False,
                },
            }
        }
    )

    entity_type: EntityType
    summary: AgingReportSummary
    rows: list[AgingReportRow]
    pagination: PaginationMeta


class AgingReportParams(BaseModel):
    """Query params for GET /reports/aging - mirrors OutstandingReportParams
    but with a smaller filter set (TASKS.md's own "FILTERS" section for
    this report lists no `overdue_only`/date range): buckets already
    stratify by overdue-ness, so a separate overdue toggle adds little, and
    there is no transaction-date concept to range over - aging is always
    "as of today". No `sort` field, for the same fixed-order reason as
    OutstandingReportParams."""

    entity_type: EntityType = Field(default=EntityType.CUSTOMER)
    outstanding_only: bool = Field(
        default=False, description="Restrict rows to entities with total > 0."
    )
    risk_level: RiskLevel | None = Field(default=None, description="Filter by risk_level.")
    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across the entity's name and code.",
        examples=["Konkan"],
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class TripProfitabilityRow(BaseModel):
    """One row of the Trip Profitability report - one completed trip
    (TASKS.md Sprint 11 Session 4 Phase A: "one row = one completed trip").
    `status` is always `returned` here: a trip only ever appears in this
    report once it has actually completed (a confirmed design decision -
    planned/departed trips haven't finished, cancelled trips never did) -
    still included as a displayed column for parity with the spec's own
    "COLUMNS" list, not because it varies row to row."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trip_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c07",
                "trip_number": "TRIP-2026-0042",
                "boat_id": "019f7af3-83ae-783a-b139-40a239786b40",
                "boat_name": "MV Sagar Kanya",
                "departure_date": "2026-07-01",
                "return_date": "2026-07-05",
                "status": "returned",
                "revenue": "48250.00",
                "expenses": "12500.00",
                "profit": "35750.00",
                "profit_margin_percent": "74.09",
            }
        }
    )

    trip_id: uuid.UUID
    trip_number: str
    boat_id: uuid.UUID
    boat_name: str
    departure_date: date
    return_date: date | None
    status: TripStatus
    revenue: Decimal
    expenses: Decimal
    profit: Decimal
    profit_margin_percent: Decimal


class TripProfitabilitySummary(BaseModel):
    """Computed over the FULL filtered set (every matching completed trip,
    not just the current page) - the same discipline every report in this
    module follows except Outstanding Report's own documented exception."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_revenue": "348250.00",
                "total_expenses": "95000.00",
                "total_profit": "253250.00",
                "average_profit_per_trip": "25325.00",
                "average_revenue_per_trip": "34825.00",
                "most_profitable_trip_number": "TRIP-2026-0042",
                "most_profitable_trip_profit": "35750.00",
                "loss_making_trips": 1,
            }
        }
    )

    total_revenue: Decimal
    total_expenses: Decimal
    total_profit: Decimal
    average_profit_per_trip: Decimal
    average_revenue_per_trip: Decimal
    most_profitable_trip_number: str | None
    most_profitable_trip_profit: Decimal | None
    loss_making_trips: int


class TripProfitabilityResponse(BaseModel):
    """GET /reports/trip-profitability's response body (TASKS.md Sprint 11
    Session 4 Phase A)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "summary": {
                    "total_revenue": "348250.00",
                    "total_expenses": "95000.00",
                    "total_profit": "253250.00",
                    "average_profit_per_trip": "25325.00",
                    "average_revenue_per_trip": "34825.00",
                    "most_profitable_trip_number": "TRIP-2026-0042",
                    "most_profitable_trip_profit": "35750.00",
                    "loss_making_trips": 1,
                },
                "rows": [
                    {
                        "trip_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c07",
                        "trip_number": "TRIP-2026-0042",
                        "boat_id": "019f7af3-83ae-783a-b139-40a239786b40",
                        "boat_name": "MV Sagar Kanya",
                        "departure_date": "2026-07-01",
                        "return_date": "2026-07-05",
                        "status": "returned",
                        "revenue": "48250.00",
                        "expenses": "12500.00",
                        "profit": "35750.00",
                        "profit_margin_percent": "74.09",
                    }
                ],
                "pagination": {
                    "total_records": 6,
                    "total_pages": 1,
                    "current_page": 1,
                    "page_size": 20,
                    "has_next": False,
                    "has_previous": False,
                },
            }
        }
    )

    summary: TripProfitabilitySummary
    rows: list[TripProfitabilityRow]
    pagination: PaginationMeta


class TripProfitabilityParams(BaseModel):
    """Query params for GET /reports/trip-profitability - bound via
    FastAPI's Depends() model support. There is deliberately no `status`
    filter despite TASKS.md listing "Trip Status" under FILTERS: since only
    `returned` trips are ever eligible (a hard invariant, not a toggle - see
    TripProfitabilityRow's own docstring), a status filter could only ever
    be a no-op or force zero rows, so it is not exposed. `boat_id` is an
    optional narrowing filter, not a required resource key - mirrors
    SalesReportParams.customer_id's own posture. No `sort` field: TASKS.md's
    SORTING section ("Return Date DESC, Trip Number DESC") is a fixed
    order."""

    boat_id: uuid.UUID | None = Field(default=None, description="Filter by boat.")
    from_date: date | None = Field(
        default=None, description="Inclusive lower bound on the trip's return date."
    )
    to_date: date | None = Field(
        default=None, description="Inclusive upper bound on the trip's return date."
    )
    profitability: ProfitabilityFilter | None = Field(
        default=None,
        description="Restrict to profitable (profit > 0) or loss-making (profit < 0) trips.",
    )
    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across the trip number and boat name.",
        examples=["TRIP-2026"],
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def _check_date_range(self) -> "TripProfitabilityParams":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must not be after to_date")
        return self


class BoatProfitabilityRow(BaseModel):
    """One row of the Boat Profitability report - one boat, aggregated over
    every one of its completed trips (TASKS.md Sprint 11 Session 4 Phase A:
    "one row = one boat"). A boat with zero completed trips never appears -
    there is nothing to aggregate (mirrors Outstanding Report's own "show
    only entities with real history" default)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "boat_id": "019f7af3-83ae-783a-b139-40a239786b40",
                "boat_name": "MV Sagar Kanya",
                "registration_number": "REG-2026-0007",
                "total_trips": 12,
                "revenue": "348250.00",
                "expenses": "95000.00",
                "profit": "253250.00",
                "profit_margin_percent": "72.72",
                "average_profit_per_trip": "21104.17",
                "average_revenue_per_trip": "29020.83",
                "best_trip_profit": "35750.00",
                "worst_trip_profit": "-2500.00",
                "last_trip_date": "2026-07-05",
            }
        }
    )

    boat_id: uuid.UUID
    boat_name: str
    registration_number: str
    total_trips: int
    revenue: Decimal
    expenses: Decimal
    profit: Decimal
    profit_margin_percent: Decimal
    average_profit_per_trip: Decimal
    average_revenue_per_trip: Decimal
    best_trip_profit: Decimal
    worst_trip_profit: Decimal
    last_trip_date: date | None


class BoatProfitabilitySummary(BaseModel):
    """Fleet-wide totals over the FULL filtered set (every matching boat,
    not just the current page) - `total_boats`/`active_boats` count boats
    within that same filtered set, not the tenant's entire fleet (mirrors
    Aging Report's own "summary IS scoped to filters" discipline, not
    Outstanding Report's "always full" exception - there is no two-sided
    ledger concept here that would call for that asymmetry)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fleet_revenue": "748250.00",
                "fleet_expenses": "195000.00",
                "fleet_profit": "553250.00",
                "fleet_margin_percent": "73.94",
                "total_boats": 4,
                "active_boats": 3,
                "average_profit_per_boat": "138312.50",
                "most_profitable_boat_name": "MV Sagar Kanya",
                "most_profitable_boat_profit": "253250.00",
            }
        }
    )

    fleet_revenue: Decimal
    fleet_expenses: Decimal
    fleet_profit: Decimal
    fleet_margin_percent: Decimal
    total_boats: int
    active_boats: int
    average_profit_per_boat: Decimal
    most_profitable_boat_name: str | None
    most_profitable_boat_profit: Decimal | None


class BoatProfitabilityResponse(BaseModel):
    """GET /reports/boat-profitability's response body (TASKS.md Sprint 11
    Session 4 Phase A)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "summary": {
                    "fleet_revenue": "748250.00",
                    "fleet_expenses": "195000.00",
                    "fleet_profit": "553250.00",
                    "fleet_margin_percent": "73.94",
                    "total_boats": 4,
                    "active_boats": 3,
                    "average_profit_per_boat": "138312.50",
                    "most_profitable_boat_name": "MV Sagar Kanya",
                    "most_profitable_boat_profit": "253250.00",
                },
                "rows": [
                    {
                        "boat_id": "019f7af3-83ae-783a-b139-40a239786b40",
                        "boat_name": "MV Sagar Kanya",
                        "registration_number": "REG-2026-0007",
                        "total_trips": 12,
                        "revenue": "348250.00",
                        "expenses": "95000.00",
                        "profit": "253250.00",
                        "profit_margin_percent": "72.72",
                        "average_profit_per_trip": "21104.17",
                        "average_revenue_per_trip": "29020.83",
                        "best_trip_profit": "35750.00",
                        "worst_trip_profit": "-2500.00",
                        "last_trip_date": "2026-07-05",
                    }
                ],
                "pagination": {
                    "total_records": 4,
                    "total_pages": 1,
                    "current_page": 1,
                    "page_size": 20,
                    "has_next": False,
                    "has_previous": False,
                },
            }
        }
    )

    summary: BoatProfitabilitySummary
    rows: list[BoatProfitabilityRow]
    pagination: PaginationMeta


class BoatProfitabilityParams(BaseModel):
    """Query params for GET /reports/boat-profitability - bound via
    FastAPI's Depends() model support. `boat_id` narrows to a single boat
    (used by the Boat Detail page's own Profitability tab to fetch that
    boat's Lifetime Summary). `from_date`/`to_date` bound the underlying
    trips by return date - default is All Time (TASKS.md). No `sort`
    field: TASKS.md's SORTING section ("Profit DESC, Boat Name ASC") is a
    fixed order."""

    boat_id: uuid.UUID | None = Field(default=None, description="Filter to a single boat.")
    from_date: date | None = Field(
        default=None, description="Inclusive lower bound on each underlying trip's return date."
    )
    to_date: date | None = Field(
        default=None, description="Inclusive upper bound on each underlying trip's return date."
    )
    min_trips: int | None = Field(
        default=None, ge=1, description="Restrict to boats with at least this many completed trips."
    )
    profitability: ProfitabilityFilter | None = Field(
        default=None,
        description="Restrict to profitable (profit > 0) or loss-making (profit < 0) boats.",
    )
    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across the boat's name and registration number.",
        examples=["Sagar"],
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def _check_date_range(self) -> "BoatProfitabilityParams":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must not be after to_date")
        return self


class FishSalesRow(BaseModel):
    """One row of the Fish Sales Analytics report - one fish (TASKS.md
    Sprint 11 Session 4 Phase B: "one row = one Fish"). Only fish with at
    least one qualifying sale ever appear - a fish never sold has nothing
    to aggregate. `unit` is the fish master record's own trading unit
    (`Fish.unit`), not a per-invoice-line snapshot - a report line
    aggregating quantity across many sales needs one consistent unit label,
    and a fish's trading unit is assumed stable (the same assumption
    invoice items themselves make when they snapshot it at sale time).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fish_id": "019f7af3-83ae-783a-b139-40a239786b50",
                "fish_name": "Pomfret",
                "scientific_name": "Pampus argenteus",
                "unit": "kg",
                "quantity_sold": "1250.500",
                "revenue": "375150.00",
                "average_selling_price": "300.0000",
                "invoice_count": 18,
                "trip_count": 6,
                "customer_count": 5,
                "last_sold_date": "2026-07-25",
            }
        }
    )

    fish_id: uuid.UUID
    fish_name: str
    scientific_name: str | None
    unit: FishUnit
    quantity_sold: Decimal
    revenue: Decimal
    average_selling_price: Decimal
    invoice_count: int
    trip_count: int
    customer_count: int
    last_sold_date: date | None


class FishSalesSummary(BaseModel):
    """Computed over the FULL filtered set (every matching fish, not just
    the current page) - the module's dominant summary discipline (mirrors
    Aging/Sales/Purchase/Boat Profitability, not Outstanding Report's own
    documented exception). `total_fish_sold` sums `quantity_sold` across
    every fish in the filtered set regardless of each fish's own unit - a
    known simplification (TASKS.md lists it as a single headline figure,
    not a per-unit breakdown)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_fish_sold": "4820.750",
                "total_revenue": "1284500.00",
                "average_selling_price": "266.4321",
                "best_selling_fish_name": "Pomfret",
                "best_selling_fish_quantity": "1250.500",
                "highest_revenue_fish_name": "Pomfret",
                "highest_revenue_fish_revenue": "375150.00",
                "total_fish_types_sold": 6,
            }
        }
    )

    total_fish_sold: Decimal
    total_revenue: Decimal
    average_selling_price: Decimal
    best_selling_fish_name: str | None
    best_selling_fish_quantity: Decimal | None
    highest_revenue_fish_name: str | None
    highest_revenue_fish_revenue: Decimal | None
    total_fish_types_sold: int


class FishSalesResponse(BaseModel):
    """GET /reports/fish-sales's response body (TASKS.md Sprint 11 Session
    4 Phase B)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "summary": {
                    "total_fish_sold": "4820.750",
                    "total_revenue": "1284500.00",
                    "average_selling_price": "266.4321",
                    "best_selling_fish_name": "Pomfret",
                    "best_selling_fish_quantity": "1250.500",
                    "highest_revenue_fish_name": "Pomfret",
                    "highest_revenue_fish_revenue": "375150.00",
                    "total_fish_types_sold": 6,
                },
                "rows": [
                    {
                        "fish_id": "019f7af3-83ae-783a-b139-40a239786b50",
                        "fish_name": "Pomfret",
                        "scientific_name": "Pampus argenteus",
                        "unit": "kg",
                        "quantity_sold": "1250.500",
                        "revenue": "375150.00",
                        "average_selling_price": "300.0000",
                        "invoice_count": 18,
                        "trip_count": 6,
                        "customer_count": 5,
                        "last_sold_date": "2026-07-25",
                    }
                ],
                "pagination": {
                    "total_records": 6,
                    "total_pages": 1,
                    "current_page": 1,
                    "page_size": 20,
                    "has_next": False,
                    "has_previous": False,
                },
            }
        }
    )

    summary: FishSalesSummary
    rows: list[FishSalesRow]
    pagination: PaginationMeta


class FishSalesParams(BaseModel):
    """Query params for GET /reports/fish-sales - bound via FastAPI's
    Depends() model support. Every entity filter (`fish_id`/`customer_id`/
    `boat_id`/`trip_id`) is an optional narrowing filter, not a required
    resource key - an unmatched id simply yields zero rows, mirroring
    SalesReportParams.customer_id's own posture. `from_date`/`to_date`
    bound `Invoice.invoice_date` - the only date a sale actually happened
    on. No `sort` field: TASKS.md's SORTING section ("Revenue DESC, Fish
    Name ASC") is a fixed order."""

    fish_id: uuid.UUID | None = Field(default=None, description="Filter to a single fish.")
    from_date: date | None = Field(
        default=None, description="Inclusive lower bound on the sale's invoice date."
    )
    to_date: date | None = Field(
        default=None, description="Inclusive upper bound on the sale's invoice date."
    )
    customer_id: uuid.UUID | None = Field(default=None, description="Filter by buying customer.")
    boat_id: uuid.UUID | None = Field(
        default=None, description="Filter to sales of fish caught on this boat's trips."
    )
    trip_id: uuid.UUID | None = Field(
        default=None, description="Filter to sales of fish caught on this one trip."
    )
    min_quantity: Decimal | None = Field(
        default=None, ge=0, description="Restrict to fish with quantity_sold >= this value."
    )
    min_revenue: Decimal | None = Field(
        default=None, ge=0, description="Restrict to fish with revenue >= this value."
    )
    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across the fish's code, name, local name and "
        "scientific name.",
        examples=["Pomfret"],
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def _check_date_range(self) -> "FishSalesParams":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must not be after to_date")
        return self


class FishSalesHistoryRow(BaseModel):
    """One row of the Fish Detail page's own Sales History section (TASKS.md
    Sprint 11 Session 4 Phase B) - one individual sale (one invoice item),
    unlike FishSalesRow which aggregates every sale of a fish into a single
    line. `boat_name`/`trip_number` are None when the line has no
    trip_catch_id (purchased/untracked stock - see FishSalesRow's own
    docstring)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "invoice_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c03",
                "invoice_number": "INV/2026-27/00015",
                "invoice_date": "2026-07-15",
                "customer_name": "Konkan Seafoods",
                "boat_name": "MV Sagar Kanya",
                "trip_number": "TRIP-2026-0042",
                "quantity": "100.000",
                "unit_price": "300.0000",
                "revenue": "30000.00",
            }
        }
    )

    invoice_id: uuid.UUID
    invoice_number: str
    invoice_date: date
    customer_name: str
    boat_name: str | None
    trip_number: str | None
    quantity: Decimal
    unit_price: Decimal
    revenue: Decimal


class FishSalesHistoryResponse(BaseModel):
    """GET /reports/fish-sales-history's response body (TASKS.md Sprint 11
    Session 4 Phase B) - powers the Fish Detail page's own Sales History
    section. No `summary` - the Sales Analytics tab's Lifetime Summary
    comes from GET /reports/fish-sales?fish_id=... instead (mirrors the
    Boat Detail page's own Profitability tab, which sources its Lifetime
    Summary from GET /reports/boat-profitability and its Trip History from
    GET /reports/trip-profitability)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rows": [
                    {
                        "invoice_id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c03",
                        "invoice_number": "INV/2026-27/00015",
                        "invoice_date": "2026-07-15",
                        "customer_name": "Konkan Seafoods",
                        "boat_name": "MV Sagar Kanya",
                        "trip_number": "TRIP-2026-0042",
                        "quantity": "100.000",
                        "unit_price": "300.0000",
                        "revenue": "30000.00",
                    }
                ],
                "pagination": {
                    "total_records": 18,
                    "total_pages": 1,
                    "current_page": 1,
                    "page_size": 20,
                    "has_next": False,
                    "has_previous": False,
                },
            }
        }
    )

    rows: list[FishSalesHistoryRow]
    pagination: PaginationMeta


class FishSalesHistoryParams(BaseModel):
    """Query params for GET /reports/fish-sales-history - `fish_id` is
    required (unlike every other entity filter in this module): this
    endpoint only ever powers the Fish Detail page's own Sales History
    section, not a standalone report, so there is no sensible "all fish"
    request to make. No `sort` field - rows are always ordered
    `invoice_date DESC, invoice_number DESC`, a fixed order (mirrors every
    other fixed-order report in this module)."""

    fish_id: uuid.UUID = Field(description="The fish whose sales history to return - required.")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
