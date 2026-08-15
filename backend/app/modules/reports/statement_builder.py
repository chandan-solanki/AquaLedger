"""Converts an already-fetched Customer/Supplier Ledger response (+ that
party's own profile) into `ReportExportData` for the shared export engine
(TASKS.md Sprint 11 Session 5 Phase C). Pure DTO-to-DTO transformation -
no database access, no new calculation. Every number here already came
from `ReportsService.get_customer_ledger()`/`get_supplier_ledger()`,
called unchanged by the statement API route (see
`app.modules.reports.export_dispatch`); this module only reshapes that
same ledger data into a formal statement document, dropping the
`transaction_type` column the plain ledger report shows (a business
document doesn't print an internal enum value) and adding the party's
own address/phone/GSTIN alongside a closing "system generated" note.

Customer and Supplier Ledger entries share an identical field shape
(`transaction_date`, `reference_number`, `description`, `debit`, `credit`,
`running_balance` - `transaction_type` is dropped here) despite being two
distinct Pydantic classes, so both statement types funnel through the one
`_build_statement_export_data()` helper below - no logic is duplicated
between them.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Protocol

from app.core.report_export.export_models import (
    ColumnAlignment,
    ColumnFormat,
    ReportColumn,
    ReportExportData,
    ReportFilterDisplay,
    ReportRow,
    ReportSummary,
)
from app.modules.companies.schemas import CompanyResponse
from app.modules.reports.schemas import CustomerLedgerResponse, SupplierLedgerResponse
from app.modules.suppliers.schemas import SupplierResponse

_STATEMENT_COLUMNS = [
    ReportColumn(title="Date", key="transaction_date", format=ColumnFormat.DATE),
    ReportColumn(title="Reference Number", key="reference_number"),
    ReportColumn(title="Description", key="description"),
    ReportColumn(
        title="Debit", key="debit", alignment=ColumnAlignment.RIGHT, format=ColumnFormat.CURRENCY
    ),
    ReportColumn(
        title="Credit", key="credit", alignment=ColumnAlignment.RIGHT, format=ColumnFormat.CURRENCY
    ),
    ReportColumn(
        title="Running Balance",
        key="running_balance",
        alignment=ColumnAlignment.RIGHT,
        format=ColumnFormat.CURRENCY,
    ),
]

_STATEMENT_FOOTER = "This is a system generated statement."


class _StatementEntry(Protocol):
    """`CustomerLedgerEntry`/`SupplierLedgerEntry` structural shape, minus
    `transaction_type` - a statement never prints it."""

    transaction_date: date
    reference_number: str
    description: str
    debit: Decimal
    credit: Decimal
    running_balance: Decimal


def _period_label(from_date: date | None, to_date: date | None) -> str:
    if from_date and to_date:
        return f"{from_date.isoformat()} to {to_date.isoformat()}"
    if from_date:
        return f"From {from_date.isoformat()}"
    if to_date:
        return f"Up to {to_date.isoformat()}"
    return "All Time"


def _format_company_address(company: CompanyResponse) -> str | None:
    state_and_pincode = " ".join(part for part in (company.state, company.pincode) if part)
    parts = [
        company.address_line1,
        company.address_line2,
        company.city,
        state_and_pincode,
        company.country,
    ]
    joined = ", ".join(part for part in parts if part)
    return joined or None


def _build_statement_export_data(
    *,
    statement_title: str,
    party_label: str,
    party_name: str,
    party_code: str,
    address: str | None,
    phone: str | None,
    gstin: str | None,
    from_date: date | None,
    to_date: date | None,
    opening_balance: Decimal,
    total_debit: Decimal,
    total_credit: Decimal,
    closing_balance: Decimal,
    entries: list[_StatementEntry],
    generated_by: str,
    tenant_name: str,
) -> ReportExportData:
    filters = [
        ReportFilterDisplay(label=f"{party_label} Name", value=party_name),
        ReportFilterDisplay(label=f"{party_label} Code", value=party_code),
    ]
    if address:
        filters.append(ReportFilterDisplay(label="Address", value=address))
    if phone:
        filters.append(ReportFilterDisplay(label="Phone", value=phone))
    if gstin:
        filters.append(ReportFilterDisplay(label="GST Number", value=gstin))
    filters.append(
        ReportFilterDisplay(label="Statement Period", value=_period_label(from_date, to_date))
    )

    rows = [
        ReportRow(
            data={
                "transaction_date": entry.transaction_date,
                "reference_number": entry.reference_number,
                "description": entry.description,
                "debit": entry.debit,
                "credit": entry.credit,
                "running_balance": entry.running_balance,
            }
        )
        for entry in entries
    ]

    summary = [
        ReportSummary(label="Opening Balance", value=opening_balance),
        ReportSummary(label="Total Debit", value=total_debit),
        ReportSummary(label="Total Credit", value=total_credit),
        ReportSummary(label="Closing Balance", value=closing_balance),
    ]

    return ReportExportData(
        title=statement_title,
        subtitle=f"{party_name} ({party_code})",
        filters=filters,
        columns=_STATEMENT_COLUMNS,
        rows=rows,
        summary=summary,
        generated_at=datetime.now(UTC),
        generated_by=generated_by,
        tenant_name=tenant_name,
        footer=_STATEMENT_FOOTER,
    )


def build_customer_statement_export_data(
    ledger: CustomerLedgerResponse,
    company: CompanyResponse,
    *,
    generated_by: str,
    tenant_name: str,
    from_date: date | None = None,
    to_date: date | None = None,
) -> ReportExportData:
    return _build_statement_export_data(
        statement_title="Customer Statement",
        party_label="Customer",
        party_name=ledger.customer.name,
        party_code=ledger.customer.code,
        address=_format_company_address(company),
        phone=company.phone,
        gstin=company.gstin,
        from_date=from_date,
        to_date=to_date,
        opening_balance=ledger.summary.opening_balance,
        total_debit=ledger.summary.total_debit,
        total_credit=ledger.summary.total_credit,
        closing_balance=ledger.summary.closing_balance,
        entries=list(ledger.entries),
        generated_by=generated_by,
        tenant_name=tenant_name,
    )


def build_supplier_statement_export_data(
    ledger: SupplierLedgerResponse,
    supplier: SupplierResponse,
    *,
    generated_by: str,
    tenant_name: str,
    from_date: date | None = None,
    to_date: date | None = None,
) -> ReportExportData:
    return _build_statement_export_data(
        statement_title="Supplier Statement",
        party_label="Supplier",
        party_name=ledger.supplier.name,
        party_code=ledger.supplier.code,
        address=supplier.address,
        phone=supplier.phone,
        gstin=supplier.gstin,
        from_date=from_date,
        to_date=to_date,
        opening_balance=ledger.summary.opening_balance,
        total_debit=ledger.summary.total_debit,
        total_credit=ledger.summary.total_credit,
        closing_balance=ledger.summary.closing_balance,
        entries=list(ledger.entries),
        generated_by=generated_by,
        tenant_name=tenant_name,
    )
