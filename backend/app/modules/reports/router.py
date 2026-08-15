from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

import app.core.report_export.exporters as _report_exporters  # noqa: F401 - registers PDF/Excel/CSV
from app.common.schemas import ErrorResponse
from app.core.report_export.exceptions import UnsupportedExportFormatError
from app.core.report_export.export_service import ExportService
from app.core.report_export.filenames import build_export_filename
from app.core.report_export.registry import registry as export_registry
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission
from app.modules.reports.dependencies import get_reports_service
from app.modules.reports.export_dispatch import (
    build_report_export_data,
    fetch_customer_statement_export_data,
    fetch_supplier_statement_export_data,
    parse_params,
    parse_report_type,
)
from app.modules.reports.permissions import REPORTS_VIEW
from app.modules.reports.schemas import (
    AgingReportParams,
    AgingReportResponse,
    BoatProfitabilityParams,
    BoatProfitabilityResponse,
    CustomerLedgerParams,
    CustomerLedgerResponse,
    FishSalesHistoryParams,
    FishSalesHistoryResponse,
    FishSalesParams,
    FishSalesResponse,
    OutstandingReportParams,
    OutstandingReportResponse,
    PurchaseReportParams,
    PurchaseReportResponse,
    SalesReportParams,
    SalesReportResponse,
    SupplierLedgerParams,
    SupplierLedgerResponse,
    TripProfitabilityParams,
    TripProfitabilityResponse,
)
from app.modules.reports.service import ReportsService

router = APIRouter(prefix="/reports", tags=["reports"])

_COMMON_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Missing required permission"},
}
_CUSTOMER_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "customer_id does not reference an existing company for this tenant",
    },
}
_SUPPLIER_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "supplier_id does not reference an existing supplier for this tenant",
    },
}


@router.get(
    "/customer-ledger",
    response_model=CustomerLedgerResponse,
    summary="Customer Ledger: a chronological, running-balance accounting ledger for one customer",
    description=(
        "Read-only - no create/update/delete anywhere in this module. Generated entirely "
        "from issued invoices (debit) and posted payments (credit) for the given "
        "`customer_id`, never from the cached `companies.outstanding_amount`. Draft/"
        "cancelled invoices, draft payments and soft-deleted rows are always excluded. "
        "`opening_balance` is the net balance strictly before `from_date` (0 if omitted); "
        "`closing_balance` is the final running balance after every transaction in range. "
        "`transaction_type` only narrows which rows appear in `entries` - it never changes "
        "`opening_balance`/`running_balance`/`closing_balance`/the summary totals, which "
        "always reflect the customer's true account balance."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_CUSTOMER_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission(REPORTS_VIEW))],
)
async def get_customer_ledger(
    params: Annotated[CustomerLedgerParams, Query()],
    current_user: User = Depends(get_current_user),
    service: ReportsService = Depends(get_reports_service),
) -> CustomerLedgerResponse:
    return await service.get_customer_ledger(params, tenant_id=current_user.tenant_id)


@router.get(
    "/supplier-ledger",
    response_model=SupplierLedgerResponse,
    summary="Supplier Ledger: a chronological, running-balance accounting ledger for one supplier",
    description=(
        "Read-only - no create/update/delete anywhere in this module. Generated entirely "
        "from posted purchase bills (debit) and posted supplier payments (credit) for the "
        "given `supplier_id`, never from the cached `suppliers.outstanding_amount`. Draft/"
        "cancelled purchase bills, draft supplier payments and soft-deleted rows are always "
        "excluded. `opening_balance` is the net balance strictly before `from_date` (0 if "
        "omitted); `closing_balance` is the final running balance after every transaction in "
        "range. `transaction_type` only narrows which rows appear in `entries` - it never "
        "changes `opening_balance`/`running_balance`/`closing_balance`/the summary totals, "
        "which always reflect the supplier's true account balance."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_SUPPLIER_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission(REPORTS_VIEW))],
)
async def get_supplier_ledger(
    params: Annotated[SupplierLedgerParams, Query()],
    current_user: User = Depends(get_current_user),
    service: ReportsService = Depends(get_reports_service),
) -> SupplierLedgerResponse:
    return await service.get_supplier_ledger(params, tenant_id=current_user.tenant_id)


@router.get(
    "/sales",
    response_model=SalesReportResponse,
    summary="Sales Report: every issued invoice, with server-computed summary totals",
    description=(
        "Read-only - no create/update/delete anywhere in this module. One row per issued "
        "invoice (draft invoices are always excluded). `summary` is computed over the full "
        "filtered set, not just the current page. Rows are always ordered `invoice_date "
        "DESC, invoice_number DESC` - a fixed order, not user-selectable. `customer_id` is "
        "an optional filter, not a required resource key - an unmatched id simply yields "
        "zero rows, it never 404s."
    ),
    responses=_COMMON_ERROR_RESPONSES,
    dependencies=[Depends(require_permission(REPORTS_VIEW))],
)
async def get_sales_report(
    params: Annotated[SalesReportParams, Query()],
    current_user: User = Depends(get_current_user),
    service: ReportsService = Depends(get_reports_service),
) -> SalesReportResponse:
    return await service.get_sales_report(params, tenant_id=current_user.tenant_id)


@router.get(
    "/purchases",
    response_model=PurchaseReportResponse,
    summary="Purchase Report: every posted purchase bill, with server-computed summary totals",
    description=(
        "Read-only - no create/update/delete anywhere in this module. One row per posted "
        "purchase bill (draft bills are always excluded). `summary` is computed over the "
        "full filtered set, not just the current page. Rows are always ordered `bill_date "
        "DESC, bill_number DESC` - a fixed order, not user-selectable. `supplier_id` is an "
        "optional filter, not a required resource key - an unmatched id simply yields zero "
        "rows, it never 404s."
    ),
    responses=_COMMON_ERROR_RESPONSES,
    dependencies=[Depends(require_permission(REPORTS_VIEW))],
)
async def get_purchase_report(
    params: Annotated[PurchaseReportParams, Query()],
    current_user: User = Depends(get_current_user),
    service: ReportsService = Depends(get_reports_service),
) -> PurchaseReportResponse:
    return await service.get_purchase_report(params, tenant_id=current_user.tenant_id)


@router.get(
    "/outstanding",
    response_model=OutstandingReportResponse,
    summary="Outstanding Report: every customer or supplier with any invoice/purchase-bill history",
    description=(
        "Read-only - no create/update/delete anywhere in this module. One row per business "
        "entity, never per transaction. `entity_type` selects the Customer Outstanding or "
        "Supplier Outstanding tab (defaults to `customer`). `summary` is always the full, "
        "unfiltered Accounts Receivable/Payable picture across every customer and supplier - "
        "it never changes with `entity_type` or any row filter. `risk_level` is derived "
        "dynamically every request (never stored) from how overdue an entity's oldest "
        "unpaid invoice/bill is."
    ),
    responses=_COMMON_ERROR_RESPONSES,
    dependencies=[Depends(require_permission(REPORTS_VIEW))],
)
async def get_outstanding_report(
    params: Annotated[OutstandingReportParams, Query()],
    current_user: User = Depends(get_current_user),
    service: ReportsService = Depends(get_reports_service),
) -> OutstandingReportResponse:
    return await service.get_outstanding_report(params, tenant_id=current_user.tenant_id)


@router.get(
    "/aging",
    response_model=AgingReportResponse,
    summary="Aging Report: receivables/payables bucketed by how overdue they are, by due date",
    description=(
        "Read-only - no create/update/delete anywhere in this module. One row per business "
        "entity, bucketed into Current/1-30/31-60/61-90/90+ days by due_date (never "
        "invoice_date/bill_date). `entity_type` selects the Customer/Supplier tab (defaults "
        "to `customer`). Unlike the Outstanding Report, `summary` here IS scoped to "
        "`entity_type` and every row filter - it reflects the full filtered set, not just "
        "the current page."
    ),
    responses=_COMMON_ERROR_RESPONSES,
    dependencies=[Depends(require_permission(REPORTS_VIEW))],
)
async def get_aging_report(
    params: Annotated[AgingReportParams, Query()],
    current_user: User = Depends(get_current_user),
    service: ReportsService = Depends(get_reports_service),
) -> AgingReportResponse:
    return await service.get_aging_report(params, tenant_id=current_user.tenant_id)


@router.get(
    "/trip-profitability",
    response_model=TripProfitabilityResponse,
    summary="Trip Profitability: revenue, expenses and profit for every completed trip",
    description=(
        "Read-only - no create/update/delete anywhere in this module. One row per "
        "completed (returned) trip. Revenue is the sum of invoice items linked back to "
        "that trip's catches (excluding draft/cancelled invoices); expenses are the "
        "trip's own expense records. `summary` is computed over the full filtered set, "
        "not just the current page. Rows are always ordered `return date DESC, trip "
        "number DESC` - a fixed order, not user-selectable. `boat_id` is an optional "
        "filter, not a required resource key - an unmatched id simply yields zero rows."
    ),
    responses=_COMMON_ERROR_RESPONSES,
    dependencies=[Depends(require_permission(REPORTS_VIEW))],
)
async def get_trip_profitability(
    params: Annotated[TripProfitabilityParams, Query()],
    current_user: User = Depends(get_current_user),
    service: ReportsService = Depends(get_reports_service),
) -> TripProfitabilityResponse:
    return await service.get_trip_profitability(params, tenant_id=current_user.tenant_id)


@router.get(
    "/boat-profitability",
    response_model=BoatProfitabilityResponse,
    summary="Boat Profitability: revenue, expenses and profit aggregated per boat",
    description=(
        "Read-only - no create/update/delete anywhere in this module. One row per boat, "
        "aggregating every one of its completed trips (built on the same underlying "
        "calculation as GET /reports/trip-profitability, never duplicated). A boat with "
        "zero completed trips in the requested range never appears. `summary` (fleet "
        "totals, total/active boat counts) reflects the full filtered set, not just the "
        "current page. Rows are always ordered `profit DESC, boat name ASC` - a fixed "
        "order, not user-selectable. Default range is All Time; `boat_id` narrows to a "
        "single boat (used by the Boat Detail page's own Profitability tab)."
    ),
    responses=_COMMON_ERROR_RESPONSES,
    dependencies=[Depends(require_permission(REPORTS_VIEW))],
)
async def get_boat_profitability(
    params: Annotated[BoatProfitabilityParams, Query()],
    current_user: User = Depends(get_current_user),
    service: ReportsService = Depends(get_reports_service),
) -> BoatProfitabilityResponse:
    return await service.get_boat_profitability(params, tenant_id=current_user.tenant_id)


@router.get(
    "/fish-sales",
    response_model=FishSalesResponse,
    summary="Fish Sales Analytics: revenue, quantity and reach for every sold fish",
    description=(
        "Read-only - no create/update/delete anywhere in this module. One row per fish - "
        "only fish with at least one qualifying sale ever appear. Revenue and quantity are "
        "computed entirely from invoice items (never trip catch quantity), excluding draft/"
        "cancelled invoices. `summary` is computed over the full filtered set, not just the "
        "current page. Rows are always ordered `revenue DESC, fish name ASC` - a fixed "
        "order, not user-selectable. Every entity filter (fish_id/customer_id/boat_id/"
        "trip_id) is optional - an unmatched id simply yields zero rows."
    ),
    responses=_COMMON_ERROR_RESPONSES,
    dependencies=[Depends(require_permission(REPORTS_VIEW))],
)
async def get_fish_sales(
    params: Annotated[FishSalesParams, Query()],
    current_user: User = Depends(get_current_user),
    service: ReportsService = Depends(get_reports_service),
) -> FishSalesResponse:
    return await service.get_fish_sales(params, tenant_id=current_user.tenant_id)


@router.get(
    "/fish-sales-history",
    response_model=FishSalesHistoryResponse,
    summary="Fish Sales History: every individual sale of one fish, for the Fish Detail page",
    description=(
        "Read-only - no create/update/delete anywhere in this module. One row per "
        "individual sale (one invoice item) of the given `fish_id`, excluding draft/"
        "cancelled invoices. Powers the Fish Detail page's own Sales History section, not "
        "a standalone report - `fish_id` is required. Rows are always ordered "
        "`invoice_date DESC, invoice_number DESC` - a fixed order, not user-selectable."
    ),
    responses=_COMMON_ERROR_RESPONSES,
    dependencies=[Depends(require_permission(REPORTS_VIEW))],
)
async def get_fish_sales_history(
    params: Annotated[FishSalesHistoryParams, Query()],
    current_user: User = Depends(get_current_user),
    service: ReportsService = Depends(get_reports_service),
) -> FishSalesHistoryResponse:
    return await service.get_fish_sales_history(params, tenant_id=current_user.tenant_id)


@router.get(
    "/export",
    summary="Export any of this module's 9 reports as PDF, Excel, or CSV",
    description=(
        "Reuses each report's own existing service method and build_*_export_data() "
        "unchanged - no report calculation is duplicated here (TASKS.md Sprint 11 "
        "Session 5 Phase B). `report` selects which of the 9 existing reports to export "
        "(customer_ledger, supplier_ledger, sales_report, purchase_report, "
        "outstanding_report, aging_report, trip_profitability, boat_profitability, "
        "fish_sales); `format` selects pdf, excel, or csv. Every other query parameter is "
        "that report's own existing filter set (see its own GET endpoint above) - `page`/"
        "`page_size` are ignored, since an export always contains every matching row, "
        "never just one page of it."
    ),
    responses=_COMMON_ERROR_RESPONSES,
    dependencies=[Depends(require_permission(REPORTS_VIEW))],
)
async def export_report(
    request: Request,
    report: Annotated[str, Query(description="Which report to export, e.g. 'fish_sales'.")],
    format: Annotated[str, Query(description="Export format: pdf, excel, or csv.")],
    current_user: User = Depends(get_current_user),
    service: ReportsService = Depends(get_reports_service),
    session: AsyncSession = Depends(get_db),
) -> Response:
    report_type = parse_report_type(report)
    export_data = await build_report_export_data(
        service,
        session,
        report_type=report_type,
        query_params=dict(request.query_params),
        tenant_id=current_user.tenant_id,
        generated_by=current_user.full_name,
    )

    content = ExportService().export(
        export_data, report_type=report_type.value, export_format=format
    )
    exporter_cls = export_registry.get(format)  # already validated by export() above

    filename = build_export_filename(export_data, extension=exporter_cls.file_extension)
    return Response(
        content=content,
        media_type=exporter_cls.content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


_STATEMENT_FORMATS = {"pdf", "excel"}


def _check_statement_format(format: str) -> None:
    """Statements never support CSV (TASKS.md Sprint 11 Session 5 Phase
    C: "If CSV requested -> Return clean validation error") - checked
    here, before any ledger data is even fetched, reusing the exact same
    `UnsupportedExportFormatError` the generic /export endpoint's
    ExportService.export() would raise for any other unregistered
    format."""
    if format not in _STATEMENT_FORMATS:
        raise UnsupportedExportFormatError(f"Statements only support pdf or excel, not {format!r}.")


@router.get(
    "/customer-statement",
    summary="Customer Statement: a formal PDF/Excel statement of account for one customer",
    description=(
        "A business document, not a report - reuses GET /reports/customer-ledger's own "
        "service call unchanged (TASKS.md Sprint 11 Session 5 Phase C): no ledger "
        "calculation or query is duplicated here, only reshaped into a formal statement "
        "with the customer's own address/phone/GSTIN. Always includes every transaction "
        "in the requested range, regardless of `page`/`page_size` - a statement is never "
        "paginated. CSV is not a supported statement format; requesting it returns a 422."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_CUSTOMER_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission(REPORTS_VIEW))],
)
async def export_customer_statement(
    request: Request,
    format: Annotated[str, Query(description="Export format: pdf or excel. csv is not supported.")],
    current_user: User = Depends(get_current_user),
    service: ReportsService = Depends(get_reports_service),
    session: AsyncSession = Depends(get_db),
) -> Response:
    _check_statement_format(format)
    params = parse_params(CustomerLedgerParams, dict(request.query_params))

    export_data = await fetch_customer_statement_export_data(
        service,
        session,
        params=params,
        tenant_id=current_user.tenant_id,
        generated_by=current_user.full_name,
    )

    content = ExportService().export(
        export_data, report_type="customer_statement", export_format=format
    )
    exporter_cls = export_registry.get(format)

    filename = build_export_filename(export_data, extension=exporter_cls.file_extension)
    return Response(
        content=content,
        media_type=exporter_cls.content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/supplier-statement",
    summary="Supplier Statement: a formal PDF/Excel statement of account for one supplier",
    description=(
        "Mirrors GET /reports/customer-statement exactly, on the buy side - reuses GET "
        "/reports/supplier-ledger's own service call unchanged. CSV is not a supported "
        "statement format; requesting it returns a 422."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_SUPPLIER_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission(REPORTS_VIEW))],
)
async def export_supplier_statement(
    request: Request,
    format: Annotated[str, Query(description="Export format: pdf or excel. csv is not supported.")],
    current_user: User = Depends(get_current_user),
    service: ReportsService = Depends(get_reports_service),
    session: AsyncSession = Depends(get_db),
) -> Response:
    _check_statement_format(format)
    params = parse_params(SupplierLedgerParams, dict(request.query_params))

    export_data = await fetch_supplier_statement_export_data(
        service,
        session,
        params=params,
        tenant_id=current_user.tenant_id,
        generated_by=current_user.full_name,
    )

    content = ExportService().export(
        export_data, report_type="supplier_statement", export_format=format
    )
    exporter_cls = export_registry.get(format)

    filename = build_export_filename(export_data, extension=exporter_cls.file_extension)
    return Response(
        content=content,
        media_type=exporter_cls.content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
