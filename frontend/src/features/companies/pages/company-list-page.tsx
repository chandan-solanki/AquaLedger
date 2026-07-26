"use client";

import { Building2, Plus } from "lucide-react";
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
import { getCompanyColumns } from "@/features/companies/components/company-columns";
import { useCompanyRowActions } from "@/features/companies/components/company-row-actions";
import { COMPANY_STATUS_LABELS, COMPANY_STATUS_OPTIONS } from "@/features/companies/constants/company-status";
import { useCompanies } from "@/features/companies/hooks/use-companies";
import { useCompanyFilters } from "@/features/companies/hooks/use-company-filters";
import { useDeleteCompany } from "@/features/companies/hooks/use-delete-company";
import type { CompanyFilters } from "@/features/companies/schemas/company-filters";
import type { Company } from "@/features/companies/types/company";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { useSearch } from "@/hooks/use-search";
import { normalizeApiError } from "@/utils/api-error";

interface CityFilterFieldProps {
  initialCity: string;
  onDebouncedChange: (city: string) => void;
}

/**
 * Debounces City the same way `SearchBar` debounces search text, so typing
 * doesn't push a new URL history entry per keystroke. The parent remounts
 * this only on a genuinely *external* city change (Clear All, a removed
 * filter chip, Back/Forward) via `useExternalValueKey` — never on its own
 * debounced write, which would otherwise unmount the input mid-keystroke
 * and drop focus.
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
 * The Companies list page: API integration, search, filters, sorting,
 * pagination, and row-level Delete via the shared `DeleteConfirmationDialog`.
 *
 * All filter/sort/page state lives in the URL via `useCompanyFilters`
 * (nuqs) — a refresh, a shared link, or Back/Forward all restore the exact
 * same list state, per ARCHITECTURE.md §10 (Sprint 3 Session 4). Free-text
 * fields (search, city) are debounced before they reach the URL so typing
 * doesn't spam browser history; single-choice filters (status) and explicit
 * actions (page, sort) write immediately, since each is one deliberate user
 * action and correctly deserves its own Back/Forward stop.
 */
export function CompanyListPage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = useCompanyFilters();
  const [pendingDelete, setPendingDelete] = useState<Company | null>(null);

  const [searchKey, reportSearch] = useExternalValueKey(filters.search);
  const [cityKey, reportCity] = useExternalValueKey(filters.city);

  const listQuery = useCompanies(filters);
  const deleteCompany = useDeleteCompany();
  const companies = listQuery.data?.data ?? [];
  const totalCount = listQuery.data?.meta.total_records ?? 0;
  const apiError = listQuery.isError ? normalizeApiError(listQuery.error) : null;

  const hasActiveFilters = Boolean(filters.search.trim() || filters.status || filters.city.trim());
  const isGenuinelyEmpty = !listQuery.isLoading && !apiError && totalCount === 0 && !hasActiveFilters;
  const isNoResults = !listQuery.isLoading && !apiError && totalCount === 0 && hasActiveFilters;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<CompanyFilters, "page">>) => {
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

  const onDeleteRequest = useCallback((company: Company) => setPendingDelete(company), []);
  const rowActionsFor = useCompanyRowActions(onDeleteRequest);
  const columns = useMemo(() => getCompanyColumns(rowActionsFor), [rowActionsFor]);

  const sorting = useMemo<SortingState>(
    () => [{ id: filters.sort, desc: filters.direction === "desc" }],
    [filters.sort, filters.direction]
  );

  const table = useDataTable({
    data: companies,
    columns,
    sorting,
    onSortingChange: (updater) => {
      const [next] = typeof updater === "function" ? updater(sorting) : updater;
      if (next) {
        applyFilterChange({ sort: next.id as CompanyFilters["sort"], direction: next.desc ? "desc" : "asc" });
        return;
      }
      // TanStack's default toggle is a 3-state cycle (asc -> desc ->
      // unsorted) on the already-sorted column; this list has no "unsorted"
      // concept (the backend always sorts by something), so the "unsorted"
      // step just flips direction on the current column instead of
      // clearing it - clearing here would silently no-op every click after,
      // since the controlled `sorting` state would never change again.
      applyFilterChange({ direction: filters.direction === "desc" ? "asc" : "desc" });
    },
    enableMultiSort: false,
    pageCount: Math.max(1, Math.ceil(totalCount / filters.pageSize)),
  });

  const appliedFilters: AppliedFilter[] = [
    filters.search.trim() ? { key: "search", label: `Search: "${filters.search.trim()}"` } : null,
    filters.status ? { key: "status", label: `Status: ${COMPANY_STATUS_LABELS[filters.status]}` } : null,
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
        title="Companies"
        description="Customers, suppliers and trading partners linked to your ledger."
        icon={Building2}
        primaryAction={
          hasPermission("company:create")
            ? { label: "New Company", icon: Plus, href: "/companies/new" }
            : undefined
        }
        isLoading={listQuery.isLoading}
        error={
          apiError
            ? {
                title: "Failed to load companies",
                description: apiError.message,
                onRetry: () => listQuery.refetch(),
              }
            : null
        }
        isEmpty={isGenuinelyEmpty}
        emptyState={
          <DataTableEmpty
            title="No companies yet"
            description="Companies you add will appear here."
            action={
              hasPermission("company:create") ? (
                <Button asChild size="sm">
                  <Link href="/companies/new">
                    <Plus aria-hidden />
                    New Company
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
                    placeholder="Search by name, code, phone, email, GSTIN…"
                    isLoading={listQuery.isFetching}
                    aria-label="Search companies"
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
                      options={COMPANY_STATUS_OPTIONS}
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
                  ? `No companies match "${filters.search.trim()}". Try a different search or clear your filters.`
                  : "Try adjusting your search or filters."
              }
              onClearFilters={clearAllFilters}
            />
          }
          onRowClick={
            hasPermission("company:view") ? (company) => router.push(`/companies/${company.id}`) : undefined
          }
          stickyActionColumn
          aria-label="Companies"
        />
      </ListPageTemplate>

      {pendingDelete && (
        <DeleteConfirmationDialog
          open={Boolean(pendingDelete)}
          onOpenChange={(open) => !open && setPendingDelete(null)}
          entityName={pendingDelete.name}
          entityLabel="company"
          isLoading={deleteCompany.isPending}
          onConfirm={() =>
            deleteCompany.mutate(pendingDelete.id, { onSuccess: () => setPendingDelete(null) })
          }
        />
      )}
    </>
  );
}
