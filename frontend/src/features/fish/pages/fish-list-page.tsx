"use client";

import { Fish as FishIcon, Plus } from "lucide-react";
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
import { getFishColumns } from "@/features/fish/components/fish-columns";
import { useFishRowActions } from "@/features/fish/components/fish-row-actions";
import { FISH_STATUS_LABELS, FISH_STATUS_OPTIONS } from "@/features/fish/constants/fish-status";
import { useDeleteFish } from "@/features/fish/hooks/use-delete-fish";
import { useFishFilters } from "@/features/fish/hooks/use-fish-filters";
import { useFishes } from "@/features/fish/hooks/use-fishes";
import type { FishFilters } from "@/features/fish/schemas/fish-filters";
import type { Fish } from "@/features/fish/types/fish";
import { FISH_UNIT_LABELS, FISH_UNIT_OPTIONS } from "@/features/fish/types/fish";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { useSearch } from "@/hooks/use-search";
import { normalizeApiError } from "@/utils/api-error";

interface CategoryFilterFieldProps {
  initialCategory: string;
  onDebouncedChange: (category: string) => void;
}

/**
 * Debounces Category the same way `SearchBar` debounces search text /
 * Companies' `CityFilterField` debounces City, so typing doesn't push a new
 * URL history entry per keystroke. Remounted only on a genuinely *external*
 * category change via `useExternalValueKey` — never on its own debounced
 * write, which would otherwise unmount the input mid-keystroke.
 */
function CategoryFilterField({ initialCategory, onDebouncedChange }: CategoryFilterFieldProps) {
  const category = useSearch({ initialValue: initialCategory, debounceMs: 400 });

  useEffect(() => {
    onDebouncedChange(category.debouncedValue);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category.debouncedValue]);

  return (
    <TextFilter
      label="Category"
      value={category.value}
      onChange={category.setValue}
      placeholder="Filter by category"
    />
  );
}

/**
 * The Fish list page: API integration, search, filters, sorting, pagination,
 * and row-level Delete via the shared `DeleteConfirmationDialog` — mirroring
 * `CompanyListPage`'s architecture exactly.
 *
 * All filter/sort/page state lives in the URL via `useFishFilters` (nuqs)
 * — a refresh, a shared link, or Back/Forward all restore the exact same
 * list state, per ARCHITECTURE.md §10.
 */
export function FishListPage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = useFishFilters();
  const [pendingDelete, setPendingDelete] = useState<Fish | null>(null);

  const [searchKey, reportSearch] = useExternalValueKey(filters.search);
  const [categoryKey, reportCategory] = useExternalValueKey(filters.category);

  const listQuery = useFishes(filters);
  const deleteFish = useDeleteFish();
  const fish = listQuery.data?.data ?? [];
  const totalCount = listQuery.data?.meta.total_records ?? 0;
  const apiError = listQuery.isError ? normalizeApiError(listQuery.error) : null;

  const hasActiveFilters = Boolean(
    filters.search.trim() || filters.status || filters.category.trim() || filters.unit
  );
  const isGenuinelyEmpty = !listQuery.isLoading && !apiError && totalCount === 0 && !hasActiveFilters;
  const isNoResults = !listQuery.isLoading && !apiError && totalCount === 0 && hasActiveFilters;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<FishFilters, "page">>) => {
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

  const onDeleteRequest = useCallback((fishRecord: Fish) => setPendingDelete(fishRecord), []);
  const rowActionsFor = useFishRowActions(onDeleteRequest);
  const columns = useMemo(() => getFishColumns(rowActionsFor), [rowActionsFor]);

  const sorting = useMemo<SortingState>(
    () => [{ id: filters.sort, desc: filters.direction === "desc" }],
    [filters.sort, filters.direction]
  );

  const table = useDataTable({
    data: fish,
    columns,
    sorting,
    onSortingChange: (updater) => {
      const [next] = typeof updater === "function" ? updater(sorting) : updater;
      if (next) {
        applyFilterChange({ sort: next.id as FishFilters["sort"], direction: next.desc ? "desc" : "asc" });
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
    filters.status ? { key: "status", label: `Status: ${FISH_STATUS_LABELS[filters.status]}` } : null,
    filters.category.trim() ? { key: "category", label: `Category: ${filters.category.trim()}` } : null,
    filters.unit ? { key: "unit", label: `Unit: ${FISH_UNIT_LABELS[filters.unit]}` } : null,
  ].filter((filter): filter is AppliedFilter => filter !== null);

  function removeAppliedFilter(key: string) {
    if (key === "search") applyFilterChange({ search: "" });
    if (key === "status") applyFilterChange({ status: null });
    if (key === "category") applyFilterChange({ category: "" });
    if (key === "unit") applyFilterChange({ unit: null });
  }

  return (
    <>
      <ListPageTemplate
        title="Fish"
        description="Fish master data used across trips, invoices and stock."
        icon={FishIcon}
        primaryAction={
          hasPermission("fish:manage") ? { label: "New Fish", icon: Plus, href: "/fish/new" } : undefined
        }
        isLoading={listQuery.isLoading}
        error={
          apiError
            ? {
                title: "Failed to load fish",
                description: apiError.message,
                onRetry: () => listQuery.refetch(),
              }
            : null
        }
        isEmpty={isGenuinelyEmpty}
        emptyState={
          <DataTableEmpty
            title="No fish yet"
            description="Fish records you add will appear here."
            action={
              hasPermission("fish:manage") ? (
                <Button asChild size="sm">
                  <Link href="/fish/new">
                    <Plus aria-hidden />
                    New Fish
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
                    placeholder="Search by name, code, local name, scientific name…"
                    isLoading={listQuery.isFetching}
                    aria-label="Search fish"
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
                      options={FISH_STATUS_OPTIONS}
                      value={filters.status ?? undefined}
                      onChange={(value) => applyFilterChange({ status: value ?? null })}
                    />
                    <StatusFilter
                      label="Unit"
                      options={FISH_UNIT_OPTIONS}
                      value={filters.unit ?? undefined}
                      onChange={(value) => applyFilterChange({ unit: value ?? null })}
                    />
                    <CategoryFilterField
                      key={categoryKey}
                      initialCategory={filters.category}
                      onDebouncedChange={(category) => {
                        reportCategory(category);
                        applyFilterChange({ category });
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
                  ? `No fish match "${filters.search.trim()}". Try a different search or clear your filters.`
                  : "Try adjusting your search or filters."
              }
              onClearFilters={clearAllFilters}
            />
          }
          onRowClick={
            hasPermission("fish:view") ? (fishRecord) => router.push(`/fish/${fishRecord.id}`) : undefined
          }
          stickyActionColumn
          aria-label="Fish"
        />
      </ListPageTemplate>

      {pendingDelete && (
        <DeleteConfirmationDialog
          open={Boolean(pendingDelete)}
          onOpenChange={(open) => !open && setPendingDelete(null)}
          entityName={pendingDelete.name}
          entityLabel="fish record"
          isLoading={deleteFish.isPending}
          onConfirm={() => deleteFish.mutate(pendingDelete.id, { onSuccess: () => setPendingDelete(null) })}
        />
      )}
    </>
  );
}
