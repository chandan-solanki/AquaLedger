"use client";

import { Plus, Route } from "lucide-react";
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
import { AdvancedFilter, AppliedFilters, SearchBar, StatusFilter } from "@/components/filters";
import type { AppliedFilter } from "@/components/filters";
import { SearchableSelect } from "@/components/form";
import { ListPageTemplate } from "@/components/templates/list-page-template";
import { Button } from "@/components/ui/button";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { getTripColumns } from "@/features/trips/components/trip-columns";
import { useTripRowActions } from "@/features/trips/components/trip-row-actions";
import { TRIP_STATUS_LABELS, TRIP_STATUS_OPTIONS } from "@/features/trips/constants/trip-status";
import { useBoatOptions } from "@/features/trips/hooks/use-boat-options";
import { useDeleteTrip } from "@/features/trips/hooks/use-delete-trip";
import { useTripFilters } from "@/features/trips/hooks/use-trip-filters";
import { useTrips } from "@/features/trips/hooks/use-trips";
import type { TripFilters } from "@/features/trips/schemas/trip-filters";
import type { Trip } from "@/features/trips/types/trip";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { normalizeApiError } from "@/utils/api-error";

/**
 * The Trip list page: API integration, search, filters, sorting, pagination,
 * the "New Trip" entry point, and row-level View/Edit/Delete — mirroring
 * `BoatListPage`'s architecture exactly. Row-click navigates to
 * `/trips/{id}` (permission-gated on `trip:view`) and the row-actions menu
 * wires View/Edit/Delete, all against the backend's actual
 * `trip:view`/`trip:edit`/`trip:delete` codes (app/modules/trips/permissions.py).
 *
 * All filter/sort/page state lives in the URL via `useTripFilters` (nuqs)
 * — a refresh, a shared link, or Back/Forward all restore the exact same
 * list state, per ARCHITECTURE.md §10.
 */
export function TripListPage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = useTripFilters();
  const [searchKey, reportSearch] = useExternalValueKey(filters.search);
  const [pendingDelete, setPendingDelete] = useState<Trip | null>(null);

  const listQuery = useTrips(filters);
  const boatOptions = useBoatOptions();
  const deleteTrip = useDeleteTrip();
  const trips = listQuery.data?.data ?? [];
  const totalCount = listQuery.data?.meta.total_records ?? 0;
  const apiError = listQuery.isError ? normalizeApiError(listQuery.error) : null;

  const hasActiveFilters = Boolean(filters.search.trim() || filters.status || filters.boat);
  const isGenuinelyEmpty = !listQuery.isLoading && !apiError && totalCount === 0 && !hasActiveFilters;
  const isNoResults = !listQuery.isLoading && !apiError && totalCount === 0 && hasActiveFilters;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<TripFilters, "page">>) => {
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

  const onDeleteRequest = useCallback((trip: Trip) => setPendingDelete(trip), []);
  const rowActionsFor = useTripRowActions(onDeleteRequest);
  const columns = useMemo(
    () => getTripColumns(rowActionsFor, boatOptions.nameById),
    [rowActionsFor, boatOptions.nameById]
  );

  const sorting = useMemo<SortingState>(
    () => [{ id: filters.sort, desc: filters.direction === "desc" }],
    [filters.sort, filters.direction]
  );

  const table = useDataTable({
    data: trips,
    columns,
    sorting,
    onSortingChange: (updater) => {
      const [next] = typeof updater === "function" ? updater(sorting) : updater;
      if (next) {
        applyFilterChange({ sort: next.id as TripFilters["sort"], direction: next.desc ? "desc" : "asc" });
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
    filters.status ? { key: "status", label: `Status: ${TRIP_STATUS_LABELS[filters.status]}` } : null,
    filters.boat
      ? { key: "boat", label: `Boat: ${boatOptions.nameById.get(filters.boat) ?? filters.boat}` }
      : null,
  ].filter((filter): filter is AppliedFilter => filter !== null);

  function removeAppliedFilter(key: string) {
    if (key === "search") applyFilterChange({ search: "" });
    if (key === "status") applyFilterChange({ status: null });
    if (key === "boat") applyFilterChange({ boat: null });
  }

  return (
    <>
      <ListPageTemplate
        title="Trips"
        description="Fishing and transport trips logged by your boats."
        icon={Route}
        primaryAction={
          hasPermission("trip:create") ? { label: "New Trip", icon: Plus, href: "/trips/new" } : undefined
        }
        isLoading={listQuery.isLoading}
        error={
          apiError
            ? {
                title: "Failed to load trips",
                description: apiError.message,
                onRetry: () => listQuery.refetch(),
              }
            : null
        }
        isEmpty={isGenuinelyEmpty}
        emptyState={
          <DataTableEmpty
            title="No trips yet"
            description="Trip records you log will appear here."
            action={
              hasPermission("trip:create") ? (
                <Button asChild size="sm">
                  <Link href="/trips/new">
                    <Plus aria-hidden />
                    New Trip
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
                    placeholder="Search by trip number, boat name, or captain…"
                    isLoading={listQuery.isFetching}
                    aria-label="Search trips"
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
                      options={TRIP_STATUS_OPTIONS}
                      value={filters.status ?? undefined}
                      onChange={(value) => applyFilterChange({ status: value ?? null })}
                    />
                    <SearchableSelect
                      label="Boat"
                      placeholder="All boats"
                      options={boatOptions.options}
                      value={filters.boat ?? undefined}
                      onChange={(value) => applyFilterChange({ boat: value ?? null })}
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
                  ? `No trips match "${filters.search.trim()}". Try a different search or clear your filters.`
                  : "Try adjusting your search or filters."
              }
              onClearFilters={clearAllFilters}
            />
          }
          onRowClick={hasPermission("trip:view") ? (trip) => router.push(`/trips/${trip.id}`) : undefined}
          stickyActionColumn
          aria-label="Trips"
        />
      </ListPageTemplate>

      {pendingDelete && (
        <DeleteConfirmationDialog
          open={Boolean(pendingDelete)}
          onOpenChange={(open) => !open && setPendingDelete(null)}
          entityName={pendingDelete.tripNumber}
          entityLabel="trip"
          isLoading={deleteTrip.isPending}
          onConfirm={() => deleteTrip.mutate(pendingDelete.id, { onSuccess: () => setPendingDelete(null) })}
        />
      )}
    </>
  );
}
