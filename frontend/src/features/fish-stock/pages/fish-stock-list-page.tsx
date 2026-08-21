"use client";

import { PackageSearch, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useMemo } from "react";

import {
  DataTable,
  DataTableEmpty,
  DataTableNoResults,
  DataTablePagination,
  useDataTable,
} from "@/components/data-table";
import { SearchBar, StatusFilter } from "@/components/filters";
import { PageContainer } from "@/components/layout/page-container";
import { ReportPageTemplate } from "@/components/templates/report-page-template";
import { Button } from "@/components/ui/button";
import { Forbidden } from "@/components/feedback/error-states";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { FishStockSummaryCards } from "@/features/fish-stock/components/fish-stock-summary-cards";
import { getFishStockColumns } from "@/features/fish-stock/components/fish-stock-columns";
import { FISH_STOCK_STATUS_OPTIONS } from "@/features/fish-stock/constants/fish-stock-status";
import { useFishStockFilters } from "@/features/fish-stock/hooks/use-fish-stock-filters";
import { useFishStockList } from "@/features/fish-stock/hooks/use-fish-stock-list";
import type { FishStockFilters } from "@/features/fish-stock/schemas/fish-stock-filters";
import type { FishStockRow } from "@/features/fish-stock/types/fish-stock";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { normalizeApiError } from "@/utils/api-error";

/**
 * "How much fish do we currently have available to sell?" (Sprint 15
 * Session 1's stated business goal) - a read-only operational view over the
 * backend's GET /fish-stock aggregation (Session 2), which sums TripCatch.
 * quantity_caught/sold_quantity/available_quantity/waste_quantity per fish.
 * Structured like `FishSalesPage` (Filter Bar -> Summary Cards -> Table),
 * the closest existing precedent for a fish-centric, filterable,
 * server-paginated page - but lives under Operations, not Reports, since
 * it's an operational stock view, not a sales analytics report, and there
 * is no export endpoint to wire up (none exists on the backend for this
 * resource).
 *
 * Gated on `fish:view` only (Session 2's explicit permission decision) - no
 * `stock:view` exists. A user without `fish:view` sees a Forbidden state
 * rather than an empty table, mirroring `FishSalesPage`'s own
 * `category === "forbidden"` handling.
 */
export function FishStockListPage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = useFishStockFilters();
  const [searchKey, reportSearch] = useExternalValueKey(filters.search);

  const listQuery = useFishStockList(filters);
  const rows = useMemo(() => listQuery.data?.data ?? [], [listQuery.data]);
  const totalCount = listQuery.data?.meta.total_records ?? 0;
  const apiError = listQuery.isError ? normalizeApiError(listQuery.error) : null;

  const hasActiveFilters = Boolean(filters.search.trim() || filters.status);
  const isGenuinelyEmpty = !listQuery.isLoading && !apiError && totalCount === 0 && !hasActiveFilters;
  const isNoResults = !listQuery.isLoading && !apiError && totalCount === 0 && hasActiveFilters;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<FishStockFilters, "page">>) => {
      setFilters({ ...patch, page: 1 });
    },
    [setFilters]
  );
  const goToPage = useCallback((page: number) => setFilters({ page }), [setFilters]);
  const setPageSize = useCallback((pageSize: number) => setFilters({ pageSize, page: 1 }), [setFilters]);
  const clearAllFilters = useCallback(() => setFilters(null), [setFilters]);

  const columns = useMemo(() => getFishStockColumns(), []);
  const table = useDataTable({
    data: rows,
    columns,
    pageCount: Math.max(1, Math.ceil(totalCount / filters.pageSize)),
  });

  if (!hasPermission("fish:view")) {
    return (
      <PageContainer>
        <Forbidden description="You don't have permission to view fish stock. Contact an administrator if you believe this is a mistake." />
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
        placeholder="Search fish…"
        isLoading={listQuery.isFetching}
        aria-label="Search fish"
        className="min-w-56 flex-1"
      />
      <StatusFilter
        label="Status"
        options={FISH_STOCK_STATUS_OPTIONS}
        value={filters.status ?? undefined}
        onChange={(value) => applyFilterChange({ status: value ?? null })}
      />
      {hasActiveFilters && (
        <Button variant="ghost" size="sm" onClick={clearAllFilters}>
          <X aria-hidden />
          Reset
        </Button>
      )}
    </div>
  );

  return (
    <ReportPageTemplate
      title="Current Fish Stock"
      description="Available fish from returned fishing trips."
      filters={filterBar}
      summary={
        listQuery.data ? <FishStockSummaryCards rows={rows} totalFishTypes={totalCount} /> : undefined
      }
      isLoading={listQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load fish stock",
              description: apiError.message,
              onRetry: () => listQuery.refetch(),
            }
          : null
      }
      isEmpty={isGenuinelyEmpty}
      emptyState={
        <DataTableEmpty
          icon={PackageSearch}
          title="No available fish stock yet"
          description="Stock appears here after fish are recorded against returned trips."
        />
      }
    >
      <DataTable
        table={table}
        isLoading={listQuery.isFetching}
        loadingRowCount={Math.min(filters.pageSize, 10)}
        isNoResults={isNoResults}
        noResultsState={
          <DataTableNoResults
            description={
              filters.search.trim()
                ? `No fish match "${filters.search.trim()}". Try a different search or clear your filters.`
                : "Try adjusting your search or filters."
            }
            onClearFilters={clearAllFilters}
          />
        }
        pagination={
          <DataTablePagination
            pageIndex={filters.page - 1}
            pageSize={filters.pageSize}
            totalCount={totalCount}
            onPageChange={(pageIndex) => goToPage(pageIndex + 1)}
            onPageSizeChange={setPageSize}
          />
        }
        onRowClick={
          hasPermission("fish:view") ? (row: FishStockRow) => router.push(`/fish-stock/${row.fishId}`) : undefined
        }
        stickyHeader
        aria-label="Fish stock"
      />
    </ReportPageTemplate>
  );
}
