"""Shared DTOs for the Report Export Engine (TASKS.md Sprint 11 Session 5
Phase A). This is the one shape every future exporter (PDF/Excel/CSV, added
in a later phase) will consume - the engine itself never queries the
database or computes a report figure; a report module converts its own
already-computed response DTOs into a `ReportExportData` via its own
`build_export_data()`-style method (see app/modules/reports/service.py) and
hands that finished object to `ExportService`.

`ReportType` is a closed list of the report identifiers this engine knows
how to validate against - it names reports, it does not implement them
(no schemas, no DB models, no calculations are imported from
app.modules.reports here), keeping this package free of report-specific
logic per the module's own design brief.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReportType(StrEnum):
    """Every report/document this engine can be asked to export - one
    entry per report shipped by app.modules.reports (Sprint 11 Sessions
    1-4) plus the two statement documents (Session 5 Phase C). Adding
    another report later means adding one value here, not changing any
    exporter or the export service's own logic."""

    CUSTOMER_LEDGER = "customer_ledger"
    SUPPLIER_LEDGER = "supplier_ledger"
    SALES_REPORT = "sales_report"
    PURCHASE_REPORT = "purchase_report"
    OUTSTANDING_REPORT = "outstanding_report"
    AGING_REPORT = "aging_report"
    TRIP_PROFITABILITY = "trip_profitability"
    BOAT_PROFITABILITY = "boat_profitability"
    FISH_SALES = "fish_sales"
    CUSTOMER_STATEMENT = "customer_statement"
    SUPPLIER_STATEMENT = "supplier_statement"


class ColumnAlignment(StrEnum):
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"


class ColumnFormat(StrEnum):
    """How an exporter should render a column's raw value - declared here,
    never applied here. A PDF/Excel/CSV exporter (added in a later phase)
    reads this to decide formatting; this engine passes native Python
    values (Decimal/date/int/str/None) through untouched."""

    TEXT = "text"
    DATE = "date"
    DATETIME = "datetime"
    CURRENCY = "currency"
    NUMBER = "number"
    PERCENT = "percent"


class ReportColumn(BaseModel):
    """One column of an exportable report table."""

    model_config = ConfigDict(frozen=True)

    title: str
    key: str
    alignment: ColumnAlignment = ColumnAlignment.LEFT
    format: ColumnFormat = ColumnFormat.TEXT


class ReportRow(BaseModel):
    """One exportable row, keyed by each `ReportColumn.key` - values are
    left in their native type (Decimal/date/int/str/None); formatting is
    always an exporter's responsibility, never this layer's."""

    model_config = ConfigDict(frozen=True)

    data: dict[str, Any]


class ReportSummary(BaseModel):
    """One summary/KPI figure (e.g. "Total Revenue" -> Decimal("348250.00"))."""

    model_config = ConfigDict(frozen=True)

    label: str
    value: Any


class ReportFilterDisplay(BaseModel):
    """One applied-filter line for the export's header (e.g. "Date Range"
    -> "2026-07-01 to 2026-07-31") - already rendered to a display string
    by the caller, since only the caller knows how to describe its own
    filters."""

    model_config = ConfigDict(frozen=True)

    label: str
    value: str


class ReportExportData(BaseModel):
    """The one shape every exporter (PDF/Excel/CSV, added in a later
    phase) receives - assembled entirely from data a report module has
    already fetched and computed. This engine (base_exporter.py,
    export_service.py) never queries the database and never re-derives a
    figure from `rows` - `summary` is always supplied pre-computed."""

    model_config = ConfigDict(frozen=True)

    title: str
    subtitle: str | None = None
    filters: list[ReportFilterDisplay] = Field(default_factory=list)
    columns: list[ReportColumn]
    rows: list[ReportRow]
    summary: list[ReportSummary] = Field(default_factory=list)
    generated_at: datetime
    generated_by: str
    tenant_name: str
    footer: str | None = None
    # Sprint 14 (Company Profile) - optional org logo for the PDF exporter's
    # header. Set after the fact via `model_copy` in
    # app.modules.reports.export_dispatch, never threaded through every
    # report's own build_*_export_data() method: the logo is identical
    # across every report/statement a tenant exports, so there is nothing
    # report-specific about it worth plumbing through 11 separate method
    # signatures for. ExcelExporter/CSVExporter never read this field.
    tenant_logo_bytes: bytes | None = None
    tenant_logo_content_type: str | None = None

    @model_validator(mode="after")
    def _check_columns(self) -> "ReportExportData":
        if not self.columns:
            raise ValueError("ReportExportData must declare at least one column")

        keys = [column.key for column in self.columns]
        if len(keys) != len(set(keys)):
            raise ValueError("column keys must be unique")

        column_keys = set(keys)
        for index, row in enumerate(self.rows):
            missing = column_keys - row.data.keys()
            if missing:
                raise ValueError(f"row {index} is missing values for columns: {sorted(missing)}")

        return self
