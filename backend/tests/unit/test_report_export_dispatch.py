"""Unit tests for app.modules.reports.export_dispatch (TASKS.md Sprint 11
Session 5 Phase B) - the glue that maps a raw `report` string + query
params to one of the 9 existing reports' own Params class, service
method and build_*_export_data(). These are pure, DB-free tests (no
AsyncSession, no real report); `tests/integration/test_reports_export_api.py`
covers the real end-to-end flow against seeded data.
"""

import pytest
from pydantic import BaseModel

from app.core.report_export.exceptions import UnsupportedReportError
from app.core.report_export.export_models import ReportType
from app.modules.reports.export_dispatch import (
    _describe_filters,
    _fetch_all_rows,
    _ReportExportSpec,
    parse_params,
    parse_report_type,
)
from app.modules.reports.schemas import SalesReportParams


class TestParseReportType:
    def test_valid_report_returns_the_matching_enum_member(self) -> None:
        assert parse_report_type("fish_sales") is ReportType.FISH_SALES
        assert parse_report_type("customer_ledger") is ReportType.CUSTOMER_LEDGER

    def test_unknown_report_raises_unsupported_report_error(self) -> None:
        with pytest.raises(UnsupportedReportError):
            parse_report_type("not_a_real_report")


class TestParseParams:
    def test_strips_report_format_page_and_page_size_keys(self) -> None:
        params = parse_params(
            SalesReportParams,
            {
                "report": "sales_report",
                "format": "csv",
                "q": "Konkan",
                "page": "3",
                "page_size": "50",
            },
        )
        assert isinstance(params, SalesReportParams)
        assert params.q == "Konkan"
        # page/page_size fall back to Params' own defaults, not the
        # stripped query values - _fetch_all_rows drives those itself.
        assert params.page == 1
        assert params.page_size == 20

    def test_invalid_value_raises_the_apps_own_validation_error(self) -> None:
        from app.core.errors import ValidationError

        with pytest.raises(ValidationError):
            parse_params(SalesReportParams, {"customer_id": "not-a-uuid"})


class _FakePagination(BaseModel):
    total_pages: int


class _FakeRowsResponse(BaseModel):
    rows: list[str]
    pagination: _FakePagination

    def model_copy_rows(self, rows: list[str]) -> "_FakeRowsResponse":
        return self.model_copy(update={"rows": rows})


class _FakeEntriesResponse(BaseModel):
    entries: list[str]
    pagination: _FakePagination


class _FakeParams(BaseModel):
    page: int = 1
    page_size: int = 20


class TestDescribeFilters:
    def test_omits_none_and_pagination_fields(self) -> None:
        params = SalesReportParams(q="Konkan", page=2, page_size=50)
        filters = _describe_filters(params)
        labels = {f.label for f in filters}
        assert labels == {"Search"}
        assert filters[0].value == "Konkan"

    def test_uses_known_label_for_a_mapped_field(self) -> None:
        params = SalesReportParams(customer_id="019f7af3-83ae-783a-b139-40a239786b30")
        filters = _describe_filters(params)
        assert filters[0].label == "Customer"

    def test_falls_back_to_a_title_cased_label_for_an_unmapped_field(self) -> None:
        class _CustomParams(BaseModel):
            some_unmapped_field: str | None = None
            page: int = 1
            page_size: int = 20

        filters = _describe_filters(_CustomParams(some_unmapped_field="value"))
        assert filters == [type(filters[0])(label="Some Unmapped Field", value="value")]


class TestFetchAllRows:
    async def test_single_page_returns_that_pages_rows_unchanged(self) -> None:
        async def fetch(
            service: object, params: _FakeParams, tenant_id: object
        ) -> _FakeRowsResponse:
            return _FakeRowsResponse(rows=["a", "b"], pagination=_FakePagination(total_pages=1))

        spec = _ReportExportSpec(
            params_cls=_FakeParams, rows_field="rows", fetch=fetch, build=lambda *a, **k: None
        )
        result = await _fetch_all_rows(
            spec, service=object(), params=_FakeParams(), tenant_id=object()
        )
        assert result.rows == ["a", "b"]

    async def test_multiple_pages_are_concatenated_in_order(self) -> None:
        pages = {
            1: _FakeRowsResponse(rows=["a", "b"], pagination=_FakePagination(total_pages=3)),
            2: _FakeRowsResponse(rows=["c", "d"], pagination=_FakePagination(total_pages=3)),
            3: _FakeRowsResponse(rows=["e"], pagination=_FakePagination(total_pages=3)),
        }

        async def fetch(
            service: object, params: _FakeParams, tenant_id: object
        ) -> _FakeRowsResponse:
            return pages[params.page]

        spec = _ReportExportSpec(
            params_cls=_FakeParams, rows_field="rows", fetch=fetch, build=lambda *a, **k: None
        )
        result = await _fetch_all_rows(
            spec, service=object(), params=_FakeParams(), tenant_id=object()
        )
        assert result.rows == ["a", "b", "c", "d", "e"]

    async def test_honors_a_non_rows_field_name_like_entries(self) -> None:
        async def fetch(
            service: object, params: _FakeParams, tenant_id: object
        ) -> _FakeEntriesResponse:
            return _FakeEntriesResponse(
                entries=["x", "y"], pagination=_FakePagination(total_pages=1)
            )

        spec = _ReportExportSpec(
            params_cls=_FakeParams, rows_field="entries", fetch=fetch, build=lambda *a, **k: None
        )
        result = await _fetch_all_rows(
            spec, service=object(), params=_FakeParams(), tenant_id=object()
        )
        assert result.entries == ["x", "y"]

    async def test_requests_a_fixed_page_size_of_100_regardless_of_input_params(self) -> None:
        seen_page_sizes = []

        async def fetch(
            service: object, params: _FakeParams, tenant_id: object
        ) -> _FakeRowsResponse:
            seen_page_sizes.append(params.page_size)
            return _FakeRowsResponse(rows=[], pagination=_FakePagination(total_pages=1))

        spec = _ReportExportSpec(
            params_cls=_FakeParams, rows_field="rows", fetch=fetch, build=lambda *a, **k: None
        )
        await _fetch_all_rows(
            spec, service=object(), params=_FakeParams(page=5, page_size=10), tenant_id=object()
        )
        assert seen_page_sizes == [100]
