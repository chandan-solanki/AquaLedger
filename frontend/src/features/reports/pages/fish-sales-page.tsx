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
import { DateRangeFilter, SearchBar } from "@/components/filters";
import { NumberInput, SearchableSelect } from "@/components/form";
import { PageContainer } from "@/components/layout/page-container";
import { ExportMenu } from "@/components/reports";
import { ReportPageTemplate } from "@/components/templates/report-page-template";
import { Button } from "@/components/ui/button";
import { Forbidden } from "@/components/feedback/error-states";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { FishSalesSummaryCards } from "@/features/reports/components/fish-sales-summary-cards";
import { getFishSalesColumns } from "@/features/reports/components/fish-sales-columns";
import { useBoatOptions } from "@/features/reports/hooks/use-boat-options";
import { useCustomerOptions } from "@/features/reports/hooks/use-customer-options";
import { useFishOptions } from "@/features/reports/hooks/use-fish-options";
import { useFishSales } from "@/features/reports/hooks/use-fish-sales";
import { useFishSalesFilters } from "@/features/reports/hooks/use-fish-sales-filters";
import { useTripOptions } from "@/features/reports/hooks/use-trip-options";
import { toFishSalesParams, type FishSalesFilters } from "@/features/reports/schemas/fish-sales-filters";
import type { FishSalesRow } from "@/features/reports/types/fish-sales";
import { triggerReportDownload } from "@/features/reports/utils/trigger-report-download";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { normalizeApiError } from "@/utils/api-error";

function toDateRange(filters: FishSalesFilters): DateRange | undefined {
  if (!filters.fromDate && !filters.toDate) return undefined;
  return {
    from: filters.fromDate ? parseISO(filters.fromDate) : undefined,
    to: filters.toDate ? parseISO(filters.toDate) : undefined,
  };
}

const ISO_DATE_FORMAT = "yyyy-MM-dd";

/**
 * The Fish Sales Analytics report page (TASKS.md Sprint 11 Session 4 Phase
 * B) - Filter Bar -> Summary Cards -> Report Table, entirely driven by the
 * backend's single GET /reports/fish-sales response. One row is one sold
 * fish. Clicking a row navigates to the existing Fish Detail page, gated
 * on `fish:view` (a user with `reports:view` alone can see the report but
 * not necessarily drill into a fish record) - mirrors `SalesReportPage`'s
 * own drill-down gating.
 */
export function FishSalesPage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = useFishSalesFilters();
  const [searchKey, reportSearch] = useExternalValueKey(filters.search);
  const fishOptions = useFishOptions();
  const customerOptions = useCustomerOptions();
  const boatOptions = useBoatOptions();
  const tripOptions = useTripOptions();
  const query = useFishSales(filters);

  const data = query.data;
  const apiError = query.isError ? normalizeApiError(query.error) : null;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<FishSalesFilters, "page">>) => {
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
      filters.fishId ||
      filters.customerId ||
      filters.boatId ||
      filters.tripId ||
      filters.fromDate ||
      filters.toDate ||
      filters.minQuantity ||
      filters.minRevenue
  );

  const rows = useMemo(() => data?.rows ?? [], [data]);
  const columns = useMemo(() => getFishSalesColumns(), []);
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
        placeholder="Search by fish name, code or scientific name…"
        isLoading={query.isFetching}
        aria-label="Search fish"
        className="min-w-56 flex-1"
      />
      <SearchableSelect
        label="Fish"
        placeholder="All fish"
        options={fishOptions.options}
        value={filters.fishId ?? undefined}
        onChange={(value) => applyFilterChange({ fishId: value ?? null })}
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
      <SearchableSelect
        label="Customer"
        placeholder="All customers"
        options={customerOptions.options}
        value={filters.customerId ?? undefined}
        onChange={(value) => applyFilterChange({ customerId: value ?? null })}
      />
      <SearchableSelect
        label="Boat"
        placeholder="All boats"
        options={boatOptions.options}
        value={filters.boatId ?? undefined}
        onChange={(value) => applyFilterChange({ boatId: value ?? null })}
      />
      <SearchableSelect
        label="Trip"
        placeholder="All trips"
        options={tripOptions.options}
        value={filters.tripId ?? undefined}
        onChange={(value) => applyFilterChange({ tripId: value ?? null })}
      />
      <NumberInput
        label="Minimum Quantity"
        placeholder="Any"
        decimalPlaces={3}
        value={filters.minQuantity ?? ""}
        onChange={(event) => applyFilterChange({ minQuantity: event.target.value || null })}
        className="w-28"
      />
      <NumberInput
        label="Minimum Revenue"
        placeholder="Any"
        decimalPlaces={2}
        value={filters.minRevenue ?? ""}
        onChange={(event) => applyFilterChange({ minRevenue: event.target.value || null })}
        className="w-28"
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
      title="Fish Sales Analytics"
      description="Quantity sold, revenue and reach for every sold fish."
      wide
      exportMenu={
        <ExportMenu
          onExport={(format) => triggerReportDownload("fish_sales", format, toFishSalesParams(filters))}
        />
      }
      filters={filterBar}
      summary={data ? <FishSalesSummaryCards summary={data.summary} /> : undefined}
      isLoading={query.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load the fish sales analytics report",
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
            title="No fish sold yet"
            description="Sold fish will appear here once invoices are issued."
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
          hasPermission("fish:view")
            ? (row: FishSalesRow) => router.push(`/fish/${row.fishId}`)
            : undefined
        }
        stickyHeader
        aria-label="Fish sales analytics report"
      />
    </ReportPageTemplate>
  );
}
