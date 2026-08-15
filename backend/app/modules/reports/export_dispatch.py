"""Wires the 9 existing reports (TASKS.md Sprint 11 Session 5 Phase B) and
the Customer/Supplier Statement documents (Phase C) to the shared Report
Export Engine. This is glue code that belongs to the `reports` module,
not the export engine itself - `app.core.report_export` still knows
nothing about any specific report (ReportType is just a closed list of
names); this file is what actually maps each name to its own Params
class, its own existing service method, and its own existing
`build_*_export_data()` / `build_*_statement_export_data()` method.

No repository query is duplicated here: `_fetch_all_pages` calls a
report's own existing service method repeatedly (once per page, using
the same pagination it already supports) to assemble the full filtered
result set for export, since an export must contain every matching row,
not just one page of it - shared by both the 9-report dispatch table
below and the two statement-fetching functions at the bottom of this
file.
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationError
from app.core.report_export.exceptions import UnsupportedReportError
from app.core.report_export.export_models import ReportExportData, ReportFilterDisplay, ReportType
from app.modules.auth.models import Tenant
from app.modules.companies.service import CompanyService
from app.modules.reports.schemas import (
    AgingReportParams,
    BoatProfitabilityParams,
    CustomerLedgerParams,
    CustomerLedgerResponse,
    FishSalesParams,
    OutstandingReportParams,
    PurchaseReportParams,
    SalesReportParams,
    SupplierLedgerParams,
    SupplierLedgerResponse,
    TripProfitabilityParams,
)
from app.modules.reports.service import ReportsService
from app.modules.reports.statement_builder import (
    build_customer_statement_export_data,
    build_supplier_statement_export_data,
)
from app.modules.suppliers.service import SupplierService

_EXPORT_PAGE_SIZE = 100
_EXCLUDED_QUERY_KEYS = {"report", "format", "page", "page_size"}

_FILTER_LABELS: dict[str, str] = {
    "customer_id": "Customer",
    "supplier_id": "Supplier",
    "boat_id": "Boat",
    "trip_id": "Trip",
    "fish_id": "Fish",
    "from_date": "From Date",
    "to_date": "To Date",
    "transaction_type": "Transaction Type",
    "status": "Status",
    "paid_status": "Paid Status",
    "q": "Search",
    "entity_type": "Entity Type",
    "outstanding_only": "Outstanding Only",
    "overdue_only": "Overdue Only",
    "risk_level": "Risk Level",
    "profitability": "Profitability",
    "min_trips": "Minimum Trips",
    "min_quantity": "Minimum Quantity",
    "min_revenue": "Minimum Revenue",
}


@dataclass(frozen=True)
class _ReportExportSpec:
    params_cls: type[BaseModel]
    rows_field: str
    fetch: Callable[[ReportsService, Any, uuid.UUID], Awaitable[BaseModel]]
    build: Callable[..., ReportExportData]


_SPECS: dict[ReportType, _ReportExportSpec] = {
    ReportType.CUSTOMER_LEDGER: _ReportExportSpec(
        params_cls=CustomerLedgerParams,
        rows_field="entries",
        fetch=lambda service, params, tenant_id: service.get_customer_ledger(
            params, tenant_id=tenant_id
        ),
        build=ReportsService.build_customer_ledger_export_data,
    ),
    ReportType.SUPPLIER_LEDGER: _ReportExportSpec(
        params_cls=SupplierLedgerParams,
        rows_field="entries",
        fetch=lambda service, params, tenant_id: service.get_supplier_ledger(
            params, tenant_id=tenant_id
        ),
        build=ReportsService.build_supplier_ledger_export_data,
    ),
    ReportType.SALES_REPORT: _ReportExportSpec(
        params_cls=SalesReportParams,
        rows_field="rows",
        fetch=lambda service, params, tenant_id: service.get_sales_report(
            params, tenant_id=tenant_id
        ),
        build=ReportsService.build_sales_report_export_data,
    ),
    ReportType.PURCHASE_REPORT: _ReportExportSpec(
        params_cls=PurchaseReportParams,
        rows_field="rows",
        fetch=lambda service, params, tenant_id: service.get_purchase_report(
            params, tenant_id=tenant_id
        ),
        build=ReportsService.build_purchase_report_export_data,
    ),
    ReportType.OUTSTANDING_REPORT: _ReportExportSpec(
        params_cls=OutstandingReportParams,
        rows_field="rows",
        fetch=lambda service, params, tenant_id: service.get_outstanding_report(
            params, tenant_id=tenant_id
        ),
        build=ReportsService.build_outstanding_report_export_data,
    ),
    ReportType.AGING_REPORT: _ReportExportSpec(
        params_cls=AgingReportParams,
        rows_field="rows",
        fetch=lambda service, params, tenant_id: service.get_aging_report(
            params, tenant_id=tenant_id
        ),
        build=ReportsService.build_aging_report_export_data,
    ),
    ReportType.TRIP_PROFITABILITY: _ReportExportSpec(
        params_cls=TripProfitabilityParams,
        rows_field="rows",
        fetch=lambda service, params, tenant_id: service.get_trip_profitability(
            params, tenant_id=tenant_id
        ),
        build=ReportsService.build_trip_profitability_export_data,
    ),
    ReportType.BOAT_PROFITABILITY: _ReportExportSpec(
        params_cls=BoatProfitabilityParams,
        rows_field="rows",
        fetch=lambda service, params, tenant_id: service.get_boat_profitability(
            params, tenant_id=tenant_id
        ),
        build=ReportsService.build_boat_profitability_export_data,
    ),
    ReportType.FISH_SALES: _ReportExportSpec(
        params_cls=FishSalesParams,
        rows_field="rows",
        fetch=lambda service, params, tenant_id: service.get_fish_sales(
            params, tenant_id=tenant_id
        ),
        build=ReportsService.build_fish_sales_export_data,
    ),
}


def parse_report_type(report: str) -> ReportType:
    """Raises the exact same `UnsupportedReportError` ExportService.export()
    itself would raise for an unknown report - resolved here first only
    because the dispatch table lookup (`_SPECS[report_type]`) needs a
    valid `ReportType` before any data can be fetched."""
    try:
        return ReportType(report)
    except ValueError as exc:
        raise UnsupportedReportError(f"Unknown report: {report!r}") from exc


def parse_params[ParamsT: BaseModel](
    params_cls: type[ParamsT], query_params: dict[str, str]
) -> ParamsT:
    """Shared by the 9-report dispatch table above and the Customer/
    Supplier Statement endpoints (`app.modules.reports.router`) - both
    need the exact same "strip report/format/page/page_size, then
    validate against this report's own Params class" step."""
    raw = {key: value for key, value in query_params.items() if key not in _EXCLUDED_QUERY_KEYS}
    try:
        return params_cls.model_validate(raw)
    except PydanticValidationError as exc:
        field_errors: dict[str, list[str]] = {}
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"])
            field_errors.setdefault(field, []).append(error["msg"])
        raise ValidationError("Invalid export parameters.", field_errors=field_errors) from exc


def _describe_filters(params: BaseModel) -> list[ReportFilterDisplay]:
    filters = []
    for field_name, value in params.model_dump(exclude={"page", "page_size"}).items():
        if value is None or value == "":
            continue
        label = _FILTER_LABELS.get(field_name, field_name.replace("_", " ").title())
        filters.append(ReportFilterDisplay(label=label, value=str(value)))
    return filters


async def _fetch_all_pages[ResponseT: BaseModel](
    fetch_page: Callable[[int], Awaitable[ResponseT]], rows_field: str
) -> ResponseT:
    """Calls `fetch_page(page)` repeatedly (page 1, then every subsequent
    page `.pagination.total_pages` reports) and returns the first page's
    response with `rows_field` replaced by every page's rows concatenated
    - shared by the 9-report dispatch table (`_fetch_all_rows` below) and
    the Customer/Supplier Statement functions at the bottom of this file,
    so pagination-walking is never duplicated between them."""
    first_response = await fetch_page(1)
    rows = list(getattr(first_response, rows_field))

    total_pages = first_response.pagination.total_pages  # type: ignore[attr-defined]
    for page in range(2, total_pages + 1):
        page_response = await fetch_page(page)
        rows.extend(getattr(page_response, rows_field))

    return first_response.model_copy(update={rows_field: rows})


async def _fetch_all_rows(
    spec: _ReportExportSpec, service: ReportsService, params: BaseModel, tenant_id: uuid.UUID
) -> BaseModel:
    async def fetch_page(page: int) -> BaseModel:
        page_params = params.model_copy(update={"page": page, "page_size": _EXPORT_PAGE_SIZE})
        return await spec.fetch(service, page_params, tenant_id)

    return await _fetch_all_pages(fetch_page, spec.rows_field)


async def _get_tenant_name(session: AsyncSession, tenant_id: uuid.UUID) -> str:
    result = await session.execute(select(Tenant.name).where(Tenant.id == tenant_id))
    return result.scalar_one()


async def build_report_export_data(
    service: ReportsService,
    session: AsyncSession,
    *,
    report_type: ReportType,
    query_params: dict[str, str],
    tenant_id: uuid.UUID,
    generated_by: str,
) -> ReportExportData:
    spec = _SPECS[report_type]
    params = parse_params(spec.params_cls, query_params)
    filters = _describe_filters(params)

    full_response = await _fetch_all_rows(spec, service, params, tenant_id)
    tenant_name = await _get_tenant_name(session, tenant_id)

    return spec.build(
        full_response, generated_by=generated_by, tenant_name=tenant_name, filters=filters
    )


# -- Customer/Supplier Statements (TASKS.md Sprint 11 Session 5 Phase C) ----
#
# Both statements reuse ReportsService.get_customer_ledger()/
# get_supplier_ledger() unchanged - the exact same ledger query and
# balance calculation the plain Customer/Supplier Ledger report already
# uses - via the same `_fetch_all_pages` primitive the 9-report dispatch
# table above uses, since a statement must show every transaction in the
# period, never just one page. `CompanyService.get()`/`SupplierService.get()`
# are called once more, after the ledger fetch already proved the id
# belongs to this tenant, purely to read the party's own profile fields
# (address/phone/GSTIN) the ledger response itself doesn't carry - no new
# repository method, no new calculation.


async def fetch_customer_statement_export_data(
    service: ReportsService,
    session: AsyncSession,
    *,
    params: CustomerLedgerParams,
    tenant_id: uuid.UUID,
    generated_by: str,
) -> ReportExportData:
    async def fetch_page(page: int) -> CustomerLedgerResponse:
        page_params = params.model_copy(update={"page": page, "page_size": _EXPORT_PAGE_SIZE})
        return await service.get_customer_ledger(page_params, tenant_id=tenant_id)

    ledger = await _fetch_all_pages(fetch_page, "entries")
    company = await CompanyService(session).get(params.customer_id, tenant_id=tenant_id)
    tenant_name = await _get_tenant_name(session, tenant_id)

    return build_customer_statement_export_data(
        ledger,
        company,
        generated_by=generated_by,
        tenant_name=tenant_name,
        from_date=params.from_date,
        to_date=params.to_date,
    )


async def fetch_supplier_statement_export_data(
    service: ReportsService,
    session: AsyncSession,
    *,
    params: SupplierLedgerParams,
    tenant_id: uuid.UUID,
    generated_by: str,
) -> ReportExportData:
    async def fetch_page(page: int) -> SupplierLedgerResponse:
        page_params = params.model_copy(update={"page": page, "page_size": _EXPORT_PAGE_SIZE})
        return await service.get_supplier_ledger(page_params, tenant_id=tenant_id)

    ledger = await _fetch_all_pages(fetch_page, "entries")
    supplier = await SupplierService(session).get(params.supplier_id, tenant_id=tenant_id)
    tenant_name = await _get_tenant_name(session, tenant_id)

    return build_supplier_statement_export_data(
        ledger,
        supplier,
        generated_by=generated_by,
        tenant_name=tenant_name,
        from_date=params.from_date,
        to_date=params.to_date,
    )
