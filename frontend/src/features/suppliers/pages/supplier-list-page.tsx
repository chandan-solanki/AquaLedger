"use client";

import { Plus, Truck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { SortingState } from "@tanstack/react-table";

import {
  DataTable,
  DataTableEmpty,
  DataTableNoResults,
  DataTablePagination,
  DataTableToolbar,
  useDataTable,
} from "@/components/data-table";
import { DeleteConfirmationDialog } from "@/components/feedback/dialogs/delete-confirmation-dialog";
import { AdvancedFilter, AppliedFilters, SearchBar, StatusFilter, TextFilter } from "@/components/filters";
import type { AppliedFilter } from "@/components/filters";
import { ListPageTemplate } from "@/components/templates/list-page-template";
import { Button } from "@/components/ui/button";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { getSupplierColumns } from "@/features/suppliers/components/supplier-columns";
import { useSupplierRowActions } from "@/features/suppliers/components/supplier-row-actions";
import { SUPPLIER_STATUS_LABELS, SUPPLIER_STATUS_OPTIONS } from "@/features/suppliers/constants/supplier-status";
import { useDeleteSupplier } from "@/features/suppliers/hooks/use-delete-supplier";
import { useSupplierFilters } from "@/features/suppliers/hooks/use-supplier-filters";
import { useSuppliers } from "@/features/suppliers/hooks/use-suppliers";
import type { SupplierFilters } from "@/features/suppliers/schemas/supplier-filters";
import type { Supplier } from "@/features/suppliers/types/supplier";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { useSearch } from "@/hooks/use-search";
import { normalizeApiError } from "@/utils/api-error";

interface CityFilterFieldProps {
  initialCity: string;
  onDebouncedChange: (city: string) => void;
}

/**
 * Debounces City the same way `SearchBar` debounces search text, so typing
 * doesn't push a new URL history entry per keystroke, mirroring Companies'
 * own `CityFilterField`. The parent remounts this only on a genuinely
 * *external* city change (Clear All, a removed filter chip, Back/Forward)
 * via `useExternalValueKey`.
 */
function CityFilterField({ initialCity, onDebouncedChange }: CityFilterFieldProps) {
  const city = useSearch({ initialValue: initialCity, debounceMs: 400 });

  useEffect(() => {
    onDebouncedChange(city.debouncedValue);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [city.debouncedValue]);

  return <TextFilter label="City" value={city.value} onChange={city.setValue} placeholder="Filter by city" />;
}

/**
 * The Suppliers list page: API integration, search, filters, sorting,
 * pagination, the "New Supplier" entry point, row navigation, and row-level
 * View/Edit/Delete, mirroring `CompanyListPage` exactly (Supplier is a flat
 * master-data record, the same shape as Company).
 *
 * All filter/sort/page state lives in the URL via `useSupplierFilters`
 * (nuqs) - a refresh, a shared link, or Back/Forward all restore the exact
 * same list state, per ARCHITECTURE.md §10.
 */
export function SupplierListPage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = useSupplierFilters();
  const [pendingDelete, setPendingDelete] = useState<Supplier | null>(null);

  const [searchKey, reportSearch] = useExternalValueKey(filters.search);
  const [cityKey, reportCity] = useExternalValueKey(filters.city);

  const listQuery = useSuppliers(filters);
  const deleteSupplier = useDeleteSupplier();
  const suppliers = listQuery.data?.data ?? [];
  const totalCount = listQuery.data?.meta.total_records ?? 0;
  const apiError = listQuery.isError ? normalizeApiError(listQuery.error) : null;

  const hasActiveFilters = Boolean(filters.search.trim() || filters.status || filters.city.trim());
  const isGenuinelyEmpty = !listQuery.isLoading && !apiError && totalCount === 0 && !hasActiveFilters;
  const isNoResults = !listQuery.isLoading && !apiError && totalCount === 0 && hasActiveFilters;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<SupplierFilters, "page">>) => {
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

  const onDeleteRequest = useCallback((supplier: Supplier) => setPendingDelete(supplier), []);
  const rowActionsFor = useSupplierRowActions(onDeleteRequest);
  const columns = useMemo(() => getSupplierColumns(rowActionsFor), [rowActionsFor]);

  const sorting = useMemo<SortingState>(
    () => [{ id: filters.sort, desc: filters.direction === "desc" }],
    [filters.sort, filters.direction]
  );

  const table = useDataTable({
    data: suppliers,
    columns,
    sorting,
    onSortingChange: (updater) => {
      const [next] = typeof updater === "function" ? updater(sorting) : updater;
      if (next) {
        applyFilterChange({ sort: next.id as SupplierFilters["sort"], direction: next.desc ? "desc" : "asc" });
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
    filters.status ? { key: "status", label: `Status: ${SUPPLIER_STATUS_LABELS[filters.status]}` } : null,
    filters.city.trim() ? { key: "city", label: `City: ${filters.city.trim()}` } : null,
  ].filter((filter): filter is AppliedFilter => filter !== null);

  function removeAppliedFilter(key: string) {
    if (key === "search") applyFilterChange({ search: "" });
    if (key === "status") applyFilterChange({ status: null });
    if (key === "city") applyFilterChange({ city: "" });
  }

  return (
    <>
      <ListPageTemplate
        title="Suppliers"
        description="Suppliers you purchase fish and goods from."
        icon={Truck}
        primaryAction={
          hasPermission("supplier:create")
            ? { label: "New Supplier", icon: Plus, href: "/suppliers/new" }
            : undefined
        }
        isLoading={listQuery.isLoading}
        error={
          apiError
            ? {
                title: "Failed to load suppliers",
                description: apiError.message,
                onRetry: () => listQuery.refetch(),
              }
            : null
        }
        isEmpty={isGenuinelyEmpty}
        emptyState={
          <DataTableEmpty
            title="No suppliers yet"
            description="Suppliers you add will appear here."
            action={
              hasPermission("supplier:create") ? (
                <Button asChild size="sm">
                  <Link href="/suppliers/new">
                    <Plus aria-hidden />
                    New Supplier
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
                    placeholder="Search by name, code, or GSTIN…"
                    isLoading={listQuery.isFetching}
                    aria-label="Search suppliers"
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
                      options={SUPPLIER_STATUS_OPTIONS}
                      value={filters.status ?? undefined}
                      onChange={(value) => applyFilterChange({ status: value ?? null })}
                    />
                    <CityFilterField
                      key={cityKey}
                      initialCity={filters.city}
                      onDebouncedChange={(city) => {
                        reportCity(city);
                        applyFilterChange({ city });
                      }}
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
                  ? `No suppliers match "${filters.search.trim()}". Try a different search or clear your filters.`
                  : "Try adjusting your search or filters."
              }
              onClearFilters={clearAllFilters}
            />
          }
          onRowClick={
            hasPermission("supplier:view") ? (supplier) => router.push(`/suppliers/${supplier.id}`) : undefined
          }
          stickyActionColumn
          aria-label="Suppliers"
        />
      </ListPageTemplate>

      {pendingDelete && (
        <DeleteConfirmationDialog
          open={Boolean(pendingDelete)}
          onOpenChange={(open) => !open && setPendingDelete(null)}
          entityName={pendingDelete.name}
          entityLabel="supplier"
          isLoading={deleteSupplier.isPending}
          onConfirm={() =>
            deleteSupplier.mutate(pendingDelete.id, { onSuccess: () => setPendingDelete(null) })
          }
        />
      )}
    </>
  );
}
