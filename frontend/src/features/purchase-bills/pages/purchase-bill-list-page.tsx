"use client";

import { FileText, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo } from "react";
import type { SortingState } from "@tanstack/react-table";

import {
  DataTable,
  DataTableEmpty,
  DataTableNoResults,
  DataTablePagination,
  DataTableToolbar,
  useDataTable,
} from "@/components/data-table";
import { AdvancedFilter, AppliedFilters, SearchBar, StatusFilter } from "@/components/filters";
import type { AppliedFilter } from "@/components/filters";
import { SearchableSelect } from "@/components/form";
import { ListPageTemplate } from "@/components/templates/list-page-template";
import { Button } from "@/components/ui/button";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { getPurchaseBillColumns } from "@/features/purchase-bills/components/purchase-bill-columns";
import { usePurchaseBillRowActions } from "@/features/purchase-bills/components/purchase-bill-row-actions";
import {
  PURCHASE_BILL_STATUS_LABELS,
  PURCHASE_BILL_STATUS_OPTIONS,
} from "@/features/purchase-bills/constants/purchase-bill-status";
import { usePurchaseBillFilters } from "@/features/purchase-bills/hooks/use-purchase-bill-filters";
import { usePurchaseBills } from "@/features/purchase-bills/hooks/use-purchase-bills";
import { useSupplierOptions } from "@/features/purchase-bills/hooks/use-supplier-options";
import type { PurchaseBillFilters } from "@/features/purchase-bills/schemas/purchase-bill-filters";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { normalizeApiError } from "@/utils/api-error";

/**
 * The Purchase Bills list page: API integration, search, filters, sorting,
 * pagination, the "New Purchase Bill" entry point, row navigation, and
 * row-level View/Edit - there is no Delete/Post row action; those remain
 * separate, later work, mirroring the scope of `usePurchaseBillRowActions`.
 * All filter/sort/page state lives in the URL via `usePurchaseBillFilters`
 * (nuqs) - a refresh, a shared link, or Back/Forward all restore the exact
 * same list state, per ARCHITECTURE.md §10.
 */
export function PurchaseBillListPage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = usePurchaseBillFilters();
  const [searchKey, reportSearch] = useExternalValueKey(filters.search);

  const listQuery = usePurchaseBills(filters);
  const supplierOptions = useSupplierOptions();
  const purchaseBills = listQuery.data?.data ?? [];
  const totalCount = listQuery.data?.meta.total_records ?? 0;
  const apiError = listQuery.isError ? normalizeApiError(listQuery.error) : null;

  const hasActiveFilters = Boolean(filters.search.trim() || filters.status || filters.supplier);
  const isGenuinelyEmpty = !listQuery.isLoading && !apiError && totalCount === 0 && !hasActiveFilters;
  const isNoResults = !listQuery.isLoading && !apiError && totalCount === 0 && hasActiveFilters;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<PurchaseBillFilters, "page">>) => {
      setFilters({ ...patch, page: 1 });
    },
    [setFilters]
  );

  const goToPage = useCallback((page: number) => setFilters({ page }), [setFilters]);
  const setPageSize = useCallback((pageSize: number) => setFilters({ pageSize, page: 1 }), [setFilters]);
  const clearAllFilters = useCallback(() => setFilters(null), [setFilters]);

  // A filter change narrowing the result set can leave `filters.page`
  // pointing past the new last page - the query would then return an empty
  // page even though earlier pages still have data, showing a misleading
  // "no results". Step back to the new last page once a completed fetch
  // confirms it's out of range.
  useEffect(() => {
    if (listQuery.isLoading || totalCount === 0) return;
    const lastPage = Math.max(1, Math.ceil(totalCount / filters.pageSize));
    if (filters.page > lastPage) goToPage(lastPage);
  }, [listQuery.isLoading, totalCount, filters.page, filters.pageSize, goToPage]);

  const rowActionsFor = usePurchaseBillRowActions();
  const columns = useMemo(
    () => getPurchaseBillColumns(rowActionsFor, supplierOptions.nameById),
    [rowActionsFor, supplierOptions.nameById]
  );

  const sorting = useMemo<SortingState>(
    () => [{ id: filters.sort, desc: filters.direction === "desc" }],
    [filters.sort, filters.direction]
  );

  const table = useDataTable({
    data: purchaseBills,
    columns,
    sorting,
    onSortingChange: (updater) => {
      const [next] = typeof updater === "function" ? updater(sorting) : updater;
      if (next) {
        applyFilterChange({
          sort: next.id as PurchaseBillFilters["sort"],
          direction: next.desc ? "desc" : "asc",
        });
        return;
      }
      // TanStack's default toggle is a 3-state cycle (asc -> desc ->
      // unsorted) on the already-sorted column; this list has no "unsorted"
      // concept (the backend always sorts by something), so the "unsorted"
      // step just flips direction on the current column instead of
      // clearing it.
      applyFilterChange({ direction: filters.direction === "desc" ? "asc" : "desc" });
    },
    enableMultiSort: false,
    pageCount: Math.max(1, Math.ceil(totalCount / filters.pageSize)),
  });

  const appliedFilters: AppliedFilter[] = [
    filters.search.trim() ? { key: "search", label: `Search: "${filters.search.trim()}"` } : null,
    filters.status
      ? { key: "status", label: `Status: ${PURCHASE_BILL_STATUS_LABELS[filters.status]}` }
      : null,
    filters.supplier
      ? {
          key: "supplier",
          label: `Supplier: ${supplierOptions.nameById.get(filters.supplier) ?? filters.supplier}`,
        }
      : null,
  ].filter((filter): filter is AppliedFilter => filter !== null);

  function removeAppliedFilter(key: string) {
    if (key === "search") applyFilterChange({ search: "" });
    if (key === "status") applyFilterChange({ status: null });
    if (key === "supplier") applyFilterChange({ supplier: null });
  }

  return (
    <ListPageTemplate
      title="Purchase Bills"
      description="Bills received from your suppliers."
      icon={FileText}
      primaryAction={
        hasPermission("purchase:create")
          ? { label: "New Purchase Bill", icon: Plus, href: "/purchase-bills/new" }
          : undefined
      }
      isLoading={listQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load purchase bills",
              description: apiError.message,
              onRetry: () => listQuery.refetch(),
            }
          : null
      }
      isEmpty={isGenuinelyEmpty}
      emptyState={
        <DataTableEmpty
          title="No purchase bills yet"
          description="Purchase bills recorded against your suppliers will appear here."
          action={
            hasPermission("purchase:create") ? (
              <Button asChild size="sm">
                <Link href="/purchase-bills/new">
                  <Plus aria-hidden />
                  New Purchase Bill
                </Link>
              </Button>
            ) : undefined
          }
        />
      }
    >
      <DataTable
        table={table}
        toolbar={
          <div className="flex flex-col gap-3">
            <DataTableToolbar
              search={
                <SearchBar
                  key={searchKey}
                  defaultValue={filters.search}
                  onSearch={(value) => {
                    reportSearch(value);
                    applyFilterChange({ search: value });
                  }}
                  placeholder="Search by bill number or supplier name…"
                  isLoading={listQuery.isFetching}
                  aria-label="Search purchase bills"
                  className="min-w-56 flex-1"
                />
              }
              filters={
                <AdvancedFilter
                  triggerLabel="Filters"
                  activeCount={appliedFilters.length}
                  onReset={hasActiveFilters ? clearAllFilters : undefined}
                  resetLabel="Clear all"
                >
                  <StatusFilter
                    label="Status"
                    options={PURCHASE_BILL_STATUS_OPTIONS}
                    value={filters.status ?? undefined}
                    onChange={(value) => applyFilterChange({ status: value ?? null })}
                  />
                  <SearchableSelect
                    label="Supplier"
                    placeholder="All suppliers"
                    options={supplierOptions.options}
                    value={filters.supplier ?? undefined}
                    onChange={(value) => applyFilterChange({ supplier: value ?? null })}
                  />
                </AdvancedFilter>
              }
            />

            <AppliedFilters
              filters={appliedFilters}
              onRemove={removeAppliedFilter}
              onClearAll={hasActiveFilters ? clearAllFilters : undefined}
            />
          </div>
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
        isLoading={listQuery.isFetching}
        loadingRowCount={Math.min(filters.pageSize, 10)}
        isNoResults={isNoResults}
        noResultsState={
          <DataTableNoResults
            description={
              filters.search.trim()
                ? `No purchase bills match "${filters.search.trim()}". Try a different search or clear your filters.`
                : "Try adjusting your search or filters."
            }
            onClearFilters={clearAllFilters}
          />
        }
        onRowClick={
          hasPermission("purchase:view")
            ? (bill) => router.push(`/purchase-bills/${bill.id}`)
            : undefined
        }
        stickyActionColumn
        aria-label="Purchase Bills"
      />
    </ListPageTemplate>
  );
}
