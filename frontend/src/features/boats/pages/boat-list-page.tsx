"use client";

import { Plus, Ship } from "lucide-react";
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
import { AdvancedFilter, AppliedFilters, BooleanFilter, SearchBar, StatusFilter, TextFilter } from "@/components/filters";
import type { AppliedFilter } from "@/components/filters";
import { ListPageTemplate } from "@/components/templates/list-page-template";
import { Button } from "@/components/ui/button";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { getBoatColumns } from "@/features/boats/components/boat-columns";
import { useBoatRowActions } from "@/features/boats/components/boat-row-actions";
import { BOAT_STATUS_LABELS, BOAT_STATUS_OPTIONS } from "@/features/boats/constants/boat-status";
import { useBoatFilters } from "@/features/boats/hooks/use-boat-filters";
import { useBoats } from "@/features/boats/hooks/use-boats";
import { useDeleteBoat } from "@/features/boats/hooks/use-delete-boat";
import type { BoatFilters } from "@/features/boats/schemas/boat-filters";
import type { Boat } from "@/features/boats/types/boat";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { useSearch } from "@/hooks/use-search";
import { normalizeApiError } from "@/utils/api-error";

interface BoatTypeFilterFieldProps {
  initialBoatType: string;
  onDebouncedChange: (boatType: string) => void;
}

/**
 * Debounces Boat Type the same way `SearchBar` debounces search text /
 * Fish's `CategoryFilterField` debounces Category, so typing doesn't push a
 * new URL history entry per keystroke. Remounted only on a genuinely
 * *external* boat type change via `useExternalValueKey` — never on its own
 * debounced write, which would otherwise unmount the input mid-keystroke.
 */
function BoatTypeFilterField({ initialBoatType, onDebouncedChange }: BoatTypeFilterFieldProps) {
  const boatType = useSearch({ initialValue: initialBoatType, debounceMs: 400 });

  useEffect(() => {
    onDebouncedChange(boatType.debouncedValue);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [boatType.debouncedValue]);

  return (
    <TextFilter
      label="Boat Type"
      value={boatType.value}
      onChange={boatType.setValue}
      placeholder="Filter by boat type"
    />
  );
}

/**
 * The Boat list page: API integration, search, filters, sorting, pagination,
 * and row-level Delete via the shared `DeleteConfirmationDialog` — mirroring
 * `CompanyListPage`'s architecture exactly. Row-click navigates to
 * `/boats/{id}` (permission-gated on `boat:view`) and the row-actions menu
 * wires View/Edit/Delete, all against the backend's actual
 * `boat:view`/`boat:edit`/`boat:delete` codes (app/modules/boats/permissions.py).
 *
 * All filter/sort/page state lives in the URL via `useBoatFilters` (nuqs)
 * — a refresh, a shared link, or Back/Forward all restore the exact same
 * list state, per ARCHITECTURE.md §10.
 */
export function BoatListPage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = useBoatFilters();
  const [pendingDelete, setPendingDelete] = useState<Boat | null>(null);

  const [searchKey, reportSearch] = useExternalValueKey(filters.search);
  const [boatTypeKey, reportBoatType] = useExternalValueKey(filters.boatType);

  const listQuery = useBoats(filters);
  const deleteBoat = useDeleteBoat();
  const boats = listQuery.data?.data ?? [];
  const totalCount = listQuery.data?.meta.total_records ?? 0;
  const apiError = listQuery.isError ? normalizeApiError(listQuery.error) : null;

  const hasActiveFilters = Boolean(
    filters.search.trim() ||
      filters.status ||
      filters.boatType.trim() ||
      filters.insuranceExpired !== null ||
      filters.licenseExpired !== null
  );
  const isGenuinelyEmpty = !listQuery.isLoading && !apiError && totalCount === 0 && !hasActiveFilters;
  const isNoResults = !listQuery.isLoading && !apiError && totalCount === 0 && hasActiveFilters;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<BoatFilters, "page">>) => {
      setFilters({ ...patch, page: 1 });
    },
    [setFilters]
  );

  const goToPage = useCallback((page: number) => setFilters({ page }), [setFilters]);
  const setPageSize = useCallback((pageSize: number) => setFilters({ pageSize, page: 1 }), [setFilters]);
  const clearAllFilters = useCallback(() => setFilters(null), [setFilters]);

  // Deleting the last row on the last page (or a filter change narrowing
  // the result set) can leave `filters.page` pointing past the new last
  // page - the query would then return an empty page even though earlier
  // pages still have data, showing a misleading "no results". Step back to
  // the new last page once a completed fetch confirms it's out of range.
  useEffect(() => {
    if (listQuery.isLoading || totalCount === 0) return;
    const lastPage = Math.max(1, Math.ceil(totalCount / filters.pageSize));
    if (filters.page > lastPage) goToPage(lastPage);
  }, [listQuery.isLoading, totalCount, filters.page, filters.pageSize, goToPage]);

  const onDeleteRequest = useCallback((boat: Boat) => setPendingDelete(boat), []);
  const rowActionsFor = useBoatRowActions(onDeleteRequest);
  const columns = useMemo(() => getBoatColumns(rowActionsFor), [rowActionsFor]);

  const sorting = useMemo<SortingState>(
    () => [{ id: filters.sort, desc: filters.direction === "desc" }],
    [filters.sort, filters.direction]
  );

  const table = useDataTable({
    data: boats,
    columns,
    sorting,
    onSortingChange: (updater) => {
      const [next] = typeof updater === "function" ? updater(sorting) : updater;
      if (next) {
        applyFilterChange({ sort: next.id as BoatFilters["sort"], direction: next.desc ? "desc" : "asc" });
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
    filters.status ? { key: "status", label: `Status: ${BOAT_STATUS_LABELS[filters.status]}` } : null,
    filters.boatType.trim() ? { key: "boatType", label: `Boat Type: ${filters.boatType.trim()}` } : null,
    filters.insuranceExpired !== null
      ? { key: "insuranceExpired", label: filters.insuranceExpired ? "Insurance: Expired" : "Insurance: Valid" }
      : null,
    filters.licenseExpired !== null
      ? { key: "licenseExpired", label: filters.licenseExpired ? "License: Expired" : "License: Valid" }
      : null,
  ].filter((filter): filter is AppliedFilter => filter !== null);

  function removeAppliedFilter(key: string) {
    if (key === "search") applyFilterChange({ search: "" });
    if (key === "status") applyFilterChange({ status: null });
    if (key === "boatType") applyFilterChange({ boatType: "" });
    if (key === "insuranceExpired") applyFilterChange({ insuranceExpired: null });
    if (key === "licenseExpired") applyFilterChange({ licenseExpired: null });
  }

  return (
    <>
      <ListPageTemplate
        title="Boats"
        description="Fishing boats owned by your business."
        icon={Ship}
        primaryAction={
          hasPermission("boat:create") ? { label: "New Boat", icon: Plus, href: "/boats/new" } : undefined
        }
        isLoading={listQuery.isLoading}
        error={
          apiError
            ? {
                title: "Failed to load boats",
                description: apiError.message,
                onRetry: () => listQuery.refetch(),
              }
            : null
        }
        isEmpty={isGenuinelyEmpty}
        emptyState={
          <DataTableEmpty
            title="No boats yet"
            description="Boat records you add will appear here."
            action={
              hasPermission("boat:create") ? (
                <Button asChild size="sm">
                  <Link href="/boats/new">
                    <Plus aria-hidden />
                    New Boat
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
                    placeholder="Search by name, code, registration number, captain…"
                    isLoading={listQuery.isFetching}
                    aria-label="Search boats"
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
                      options={BOAT_STATUS_OPTIONS}
                      value={filters.status ?? undefined}
                      onChange={(value) => applyFilterChange({ status: value ?? null })}
                    />
                    <BoatTypeFilterField
                      key={boatTypeKey}
                      initialBoatType={filters.boatType}
                      onDebouncedChange={(boatType) => {
                        reportBoatType(boatType);
                        applyFilterChange({ boatType });
                      }}
                    />
                    <BooleanFilter
                      label="Insurance Expired"
                      checked={filters.insuranceExpired ?? false}
                      onChange={(checked) => applyFilterChange({ insuranceExpired: checked ? true : null })}
                    />
                    <BooleanFilter
                      label="License Expired"
                      checked={filters.licenseExpired ?? false}
                      onChange={(checked) => applyFilterChange({ licenseExpired: checked ? true : null })}
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
                  ? `No boats match "${filters.search.trim()}". Try a different search or clear your filters.`
                  : "Try adjusting your search or filters."
              }
              onClearFilters={clearAllFilters}
            />
          }
          onRowClick={hasPermission("boat:view") ? (boat) => router.push(`/boats/${boat.id}`) : undefined}
          stickyActionColumn
          aria-label="Boats"
        />
      </ListPageTemplate>

      {pendingDelete && (
        <DeleteConfirmationDialog
          open={Boolean(pendingDelete)}
          onOpenChange={(open) => !open && setPendingDelete(null)}
          entityName={pendingDelete.name}
          entityLabel="boat"
          isLoading={deleteBoat.isPending}
          onConfirm={() => deleteBoat.mutate(pendingDelete.id, { onSuccess: () => setPendingDelete(null) })}
        />
      )}
    </>
  );
}
