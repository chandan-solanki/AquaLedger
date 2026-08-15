"use client";

import { format, parseISO } from "date-fns";
import { useRouter } from "next/navigation";
import { X } from "lucide-react";
import { useCallback, useMemo } from "react";
import type { DateRange } from "react-day-picker";

import {
  DataTable,
  DataTableEmpty,
  DataTableNoResults,
  DataTablePagination,
  useDataTable,
} from "@/components/data-table";
import { DateRangeFilter, SearchBar, StatusFilter } from "@/components/filters";
import { NumberInput, SearchableSelect } from "@/components/form";
import { PageContainer } from "@/components/layout/page-container";
import { ExportMenu } from "@/components/reports";
import { ReportPageTemplate } from "@/components/templates/report-page-template";
import { Button } from "@/components/ui/button";
import { Forbidden } from "@/components/feedback/error-states";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { BoatProfitabilitySummaryCards } from "@/features/reports/components/boat-profitability-summary-cards";
import { getBoatProfitabilityColumns } from "@/features/reports/components/boat-profitability-columns";
import { PROFITABILITY_FILTER_OPTIONS } from "@/features/reports/constants/profitability";
import { useBoatOptions } from "@/features/reports/hooks/use-boat-options";
import { useBoatProfitability } from "@/features/reports/hooks/use-boat-profitability";
import { useBoatProfitabilityFilters } from "@/features/reports/hooks/use-boat-profitability-filters";
import {
  toBoatProfitabilityParams,
  type BoatProfitabilityFilters,
} from "@/features/reports/schemas/boat-profitability-filters";
import type { BoatProfitabilityRow } from "@/features/reports/types/boat-profitability";
import { triggerReportDownload } from "@/features/reports/utils/trigger-report-download";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { normalizeApiError } from "@/utils/api-error";

function toDateRange(filters: BoatProfitabilityFilters): DateRange | undefined {
  if (!filters.fromDate && !filters.toDate) return undefined;
  return {
    from: filters.fromDate ? parseISO(filters.fromDate) : undefined,
    to: filters.toDate ? parseISO(filters.toDate) : undefined,
  };
}

const ISO_DATE_FORMAT = "yyyy-MM-dd";

/**
 * The Boat Profitability report page (TASKS.md Sprint 11 Session 4 Phase A)
 * - Filter Bar -> Summary Cards -> Report Table, entirely driven by the
 * backend's single GET /reports/boat-profitability response. One row is one
 * boat, aggregating every one of its completed trips. Default range is All
 * Time. Clicking a row navigates to the existing Boat Detail page (which
 * itself carries this same data in its own Profitability tab), gated on
 * `boat:view`.
 */
export function BoatProfitabilityPage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = useBoatProfitabilityFilters();
  const [searchKey, reportSearch] = useExternalValueKey(filters.search);
  const boatOptions = useBoatOptions();
  const query = useBoatProfitability(filters);

  const data = query.data;
  const apiError = query.isError ? normalizeApiError(query.error) : null;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<BoatProfitabilityFilters, "page">>) => {
      setFilters({ ...patch, page: 1 });
    },
    [setFilters]
  );
  const goToPage = useCallback((page: number) => setFilters({ page }), [setFilters]);
  const setPageSize = useCallback(
    (pageSize: number) => setFilters({ pageSize, page: 1 }),
    [setFilters]
  );
  const resetFilters = useCallback(() => setFilters(null), [setFilters]);

  const dateRange = useMemo(() => toDateRange(filters), [filters]);
  const hasActiveFilters = Boolean(
    filters.search.trim() ||
      filters.boatId ||
      filters.profitability ||
      filters.fromDate ||
      filters.toDate ||
      filters.minTrips
  );

  const rows = useMemo(() => data?.rows ?? [], [data]);
  const columns = useMemo(() => getBoatProfitabilityColumns(), []);
  const table = useDataTable({
    data: rows,
    columns,
    pageCount: Math.max(1, Math.ceil((data?.pagination.totalRecords ?? 0) / filters.pageSize)),
  });

  if (apiError?.category === "forbidden") {
    return (
      <PageContainer>
        <Forbidden description="You don't have permission to view accounting reports. Contact an administrator if you believe this is a mistake." />
      </PageContainer>
    );
  }

  const filterBar = (
    <div className="flex flex-wrap items-end gap-3">
      <SearchBar
        key={searchKey}
        defaultValue={filters.search}
        onSearch={(value) => {
          reportSearch(value);
          applyFilterChange({ search: value });
        }}
        placeholder="Search by boat name or registration number…"
        isLoading={query.isFetching}
        aria-label="Search boats"
        className="min-w-56 flex-1"
      />
      <SearchableSelect
        label="Boat"
        placeholder="All boats"
        options={boatOptions.options}
        value={filters.boatId ?? undefined}
        onChange={(value) => applyFilterChange({ boatId: value ?? null })}
      />
      <DateRangeFilter
        label="Date Range"
        value={dateRange}
        onChange={(range) =>
          applyFilterChange({
            fromDate: range?.from ? format(range.from, ISO_DATE_FORMAT) : null,
            toDate: range?.to ? format(range.to, ISO_DATE_FORMAT) : null,
          })
        }
      />
      <NumberInput
        label="Minimum Trips"
        placeholder="Any"
        decimalPlaces={0}
        value={filters.minTrips != null ? String(filters.minTrips) : ""}
        onChange={(event) => {
          const raw = event.target.value;
          applyFilterChange({ minTrips: raw ? Number(raw) : null });
        }}
        className="w-24"
      />
      <StatusFilter
        label="Profitability"
        options={PROFITABILITY_FILTER_OPTIONS}
        value={filters.profitability ?? undefined}
        onChange={(value) => applyFilterChange({ profitability: value ?? null })}
      />
      {hasActiveFilters && (
        <Button variant="ghost" size="sm" onClick={resetFilters}>
          <X aria-hidden />
          Reset
        </Button>
      )}
    </div>
  );

  return (
    <ReportPageTemplate
      title="Boat Profitability"
      description="Revenue, expenses and profit aggregated across every boat's completed trips."
      wide
      exportMenu={
        <ExportMenu
          onExport={(format) =>
            triggerReportDownload("boat_profitability", format, toBoatProfitabilityParams(filters))
          }
        />
      }
      filters={filterBar}
      summary={data ? <BoatProfitabilitySummaryCards summary={data.summary} /> : undefined}
      isLoading={query.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load the boat profitability report",
              description: apiError.message,
              onRetry: () => query.refetch(),
            }
          : null
      }
    >
      <DataTable
        table={table}
        isLoading={query.isFetching}
        loadingRowCount={Math.min(filters.pageSize, 10)}
        isEmpty={!query.isLoading && !apiError && rows.length === 0 && !hasActiveFilters}
        emptyState={
          <DataTableEmpty
            title="No completed trips yet"
            description="Boats will appear here once they have at least one completed trip."
          />
        }
        isNoResults={!query.isLoading && !apiError && rows.length === 0 && hasActiveFilters}
        noResultsState={<DataTableNoResults onClearFilters={resetFilters} />}
        pagination={
          <DataTablePagination
            pageIndex={filters.page - 1}
            pageSize={filters.pageSize}
            totalCount={data?.pagination.totalRecords ?? 0}
            onPageChange={(pageIndex) => goToPage(pageIndex + 1)}
            onPageSizeChange={setPageSize}
          />
        }
        onRowClick={
          hasPermission("boat:view")
            ? (row: BoatProfitabilityRow) => router.push(`/boats/${row.boatId}`)
            : undefined
        }
        stickyHeader
        aria-label="Boat profitability report"
      />
    </ReportPageTemplate>
  );
}
