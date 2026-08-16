"use client";

import { format, parseISO } from "date-fns";
import { ClipboardList, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo } from "react";
import type { DateRange } from "react-day-picker";
import type { SortingState } from "@tanstack/react-table";

import {
  DataTable,
  DataTableEmpty,
  DataTableNoResults,
  DataTablePagination,
  DataTableToolbar,
  useDataTable,
} from "@/components/data-table";
import { AdvancedFilter, AppliedFilters, DateRangeFilter, SearchBar, StatusFilter } from "@/components/filters";
import type { AppliedFilter } from "@/components/filters";
import { SearchableSelect } from "@/components/form";
import { ListPageTemplate } from "@/components/templates/list-page-template";
import { Button } from "@/components/ui/button";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { getPurchaseOrderColumns } from "@/features/purchase-orders/components/purchase-order-columns";
import { usePurchaseOrderRowActions } from "@/features/purchase-orders/components/purchase-order-row-actions";
import {
  PURCHASE_ORDER_STATUS_LABELS,
  PURCHASE_ORDER_STATUS_OPTIONS,
} from "@/features/purchase-orders/constants/purchase-order-status";
import { usePurchaseOrderFilters } from "@/features/purchase-orders/hooks/use-purchase-order-filters";
import { usePurchaseOrders } from "@/features/purchase-orders/hooks/use-purchase-orders";
import { useSupplierOptions } from "@/features/purchase-orders/hooks/use-supplier-options";
import type { PurchaseOrderFilters } from "@/features/purchase-orders/schemas/purchase-order-filters";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { normalizeApiError } from "@/utils/api-error";

function toDateRange(from: string | null, to: string | null): DateRange | undefined {
  if (!from && !to) return undefined;
  return {
    from: from ? parseISO(from) : undefined,
    to: to ? parseISO(to) : undefined,
  };
}

function toIsoDateOrNull(date: Date | undefined): string | null {
  return date ? format(date, "yyyy-MM-dd") : null;
}

/**
 * The Purchase Orders list page: API integration, search, filters, sorting,
 * pagination, the "New Purchase Order" entry point, row navigation, and
 * row-level View/Edit, mirroring `PurchaseBillListPage`. All filter/sort/
 * page state lives in the URL via `usePurchaseOrderFilters` (nuqs) - a
 * refresh, a shared link, or Back/Forward all restore the exact same list
 * state, per ARCHITECTURE.md §10.
 */
export function PurchaseOrderListPage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = usePurchaseOrderFilters();
  const [searchKey, reportSearch] = useExternalValueKey(filters.search);

  const listQuery = usePurchaseOrders(filters);
  const supplierOptions = useSupplierOptions();
  const purchaseOrders = listQuery.data?.data ?? [];
  const totalCount = listQuery.data?.meta.total_records ?? 0;
  const apiError = listQuery.isError ? normalizeApiError(listQuery.error) : null;

  const hasActiveFilters = Boolean(
    filters.search.trim() || filters.status || filters.supplier || filters.orderDateFrom || filters.orderDateTo
  );
  const isGenuinelyEmpty = !listQuery.isLoading && !apiError && totalCount === 0 && !hasActiveFilters;
  const isNoResults = !listQuery.isLoading && !apiError && totalCount === 0 && hasActiveFilters;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<PurchaseOrderFilters, "page">>) => {
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

  const rowActionsFor = usePurchaseOrderRowActions();
  const columns = useMemo(
    () => getPurchaseOrderColumns(rowActionsFor, supplierOptions.nameById),
    [rowActionsFor, supplierOptions.nameById]
  );

  const sorting = useMemo<SortingState>(
    () => [{ id: filters.sort, desc: filters.direction === "desc" }],
    [filters.sort, filters.direction]
  );

  const table = useDataTable({
    data: purchaseOrders,
    columns,
    sorting,
    onSortingChange: (updater) => {
      const [next] = typeof updater === "function" ? updater(sorting) : updater;
      if (next) {
        applyFilterChange({
          sort: next.id as PurchaseOrderFilters["sort"],
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
      ? { key: "status", label: `Status: ${PURCHASE_ORDER_STATUS_LABELS[filters.status]}` }
      : null,
    filters.supplier
      ? {
          key: "supplier",
          label: `Supplier: ${supplierOptions.nameById.get(filters.supplier) ?? filters.supplier}`,
        }
      : null,
    filters.orderDateFrom || filters.orderDateTo
      ? {
          key: "orderDate",
          label: `PO Date: ${filters.orderDateFrom ?? "…"} – ${filters.orderDateTo ?? "…"}`,
        }
      : null,
  ].filter((filter): filter is AppliedFilter => filter !== null);

  function removeAppliedFilter(key: string) {
    if (key === "search") applyFilterChange({ search: "" });
    if (key === "status") applyFilterChange({ status: null });
    if (key === "supplier") applyFilterChange({ supplier: null });
    if (key === "orderDate") applyFilterChange({ orderDateFrom: null, orderDateTo: null });
  }

  return (
    <ListPageTemplate
      title="Purchase Orders"
      description="Procurement commitments to your suppliers."
      icon={ClipboardList}
      primaryAction={
        hasPermission("purchase_order:create")
          ? { label: "New Purchase Order", icon: Plus, href: "/purchase-orders/new" }
          : undefined
      }
      isLoading={listQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load purchase orders",
              description: apiError.message,
              onRetry: () => listQuery.refetch(),
            }
          : null
      }
      isEmpty={isGenuinelyEmpty}
      emptyState={
        <DataTableEmpty
          title="No purchase orders yet"
          description="Purchase orders raised against your suppliers will appear here."
          action={
            hasPermission("purchase_order:create") ? (
              <Button asChild size="sm">
                <Link href="/purchase-orders/new">
                  <Plus aria-hidden />
                  New Purchase Order
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
                  placeholder="Search by PO number or supplier name…"
                  isLoading={listQuery.isFetching}
                  aria-label="Search purchase orders"
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
                    options={PURCHASE_ORDER_STATUS_OPTIONS}
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
                  <DateRangeFilter
                    label="PO Date"
                    value={toDateRange(filters.orderDateFrom, filters.orderDateTo)}
                    onChange={(range) =>
                      applyFilterChange({
                        orderDateFrom: toIsoDateOrNull(range?.from),
                        orderDateTo: toIsoDateOrNull(range?.to),
                      })
                    }
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
                ? `No purchase orders match "${filters.search.trim()}". Try a different search or clear your filters.`
                : "Try adjusting your search or filters."
            }
            onClearFilters={clearAllFilters}
          />
        }
        onRowClick={
          hasPermission("purchase_order:view")
            ? (order) => router.push(`/purchase-orders/${order.id}`)
            : undefined
        }
        stickyActionColumn
        aria-label="Purchase Orders"
      />
    </ListPageTemplate>
  );
}
