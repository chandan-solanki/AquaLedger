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
import { SearchableSelect } from "@/components/form";
import { PageContainer } from "@/components/layout/page-container";
import { ExportMenu } from "@/components/reports";
import { ReportPageTemplate } from "@/components/templates/report-page-template";
import { Button } from "@/components/ui/button";
import { Forbidden } from "@/components/feedback/error-states";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { TripProfitabilitySummaryCards } from "@/features/reports/components/trip-profitability-summary-cards";
import { getTripProfitabilityColumns } from "@/features/reports/components/trip-profitability-columns";
import { PROFITABILITY_FILTER_OPTIONS } from "@/features/reports/constants/profitability";
import { useBoatOptions } from "@/features/reports/hooks/use-boat-options";
import { useTripProfitability } from "@/features/reports/hooks/use-trip-profitability";
import { useTripProfitabilityFilters } from "@/features/reports/hooks/use-trip-profitability-filters";
import {
  toTripProfitabilityParams,
  type TripProfitabilityFilters,
} from "@/features/reports/schemas/trip-profitability-filters";
import type { TripProfitabilityRow } from "@/features/reports/types/trip-profitability";
import { triggerReportDownload } from "@/features/reports/utils/trigger-report-download";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { normalizeApiError } from "@/utils/api-error";

function toDateRange(filters: TripProfitabilityFilters): DateRange | undefined {
  if (!filters.fromDate && !filters.toDate) return undefined;
  return {
    from: filters.fromDate ? parseISO(filters.fromDate) : undefined,
    to: filters.toDate ? parseISO(filters.toDate) : undefined,
  };
}

const ISO_DATE_FORMAT = "yyyy-MM-dd";

/**
 * The Trip Profitability report page (TASKS.md Sprint 11 Session 4 Phase A)
 * - Filter Bar -> Summary Cards -> Report Table, entirely driven by the
 * backend's single GET /reports/trip-profitability response. One row is one
 * completed trip. Clicking a row navigates to the existing Trip Detail
 * page, gated on `trip:view` (a user with `reports:view` alone can see the
 * report but not necessarily drill into a trip) - mirrors
 * `SalesReportPage`'s own drill-down gating.
 */
export function TripProfitabilityPage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = useTripProfitabilityFilters();
  const [searchKey, reportSearch] = useExternalValueKey(filters.search);
  const boatOptions = useBoatOptions();
  const query = useTripProfitability(filters);

  const data = query.data;
  const apiError = query.isError ? normalizeApiError(query.error) : null;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<TripProfitabilityFilters, "page">>) => {
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
    filters.search.trim() || filters.boatId || filters.profitability || filters.fromDate || filters.toDate
  );

  const rows = useMemo(() => data?.rows ?? [], [data]);
  const columns = useMemo(() => getTripProfitabilityColumns(), []);
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
        placeholder="Search by trip number or boat name…"
        isLoading={query.isFetching}
        aria-label="Search trips"
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
      title="Trip Profitability"
      description="Revenue, expenses and profit for every completed trip."
      wide
      exportMenu={
        <ExportMenu
          onExport={(format) =>
            triggerReportDownload("trip_profitability", format, toTripProfitabilityParams(filters))
          }
        />
      }
      filters={filterBar}
      summary={data ? <TripProfitabilitySummaryCards summary={data.summary} /> : undefined}
      isLoading={query.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load the trip profitability report",
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
            description="Trips will appear here once they return."
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
          hasPermission("trip:view")
            ? (row: TripProfitabilityRow) => router.push(`/trips/${row.tripId}`)
            : undefined
        }
        stickyHeader
        aria-label="Trip profitability report"
      />
    </ReportPageTemplate>
  );
}
