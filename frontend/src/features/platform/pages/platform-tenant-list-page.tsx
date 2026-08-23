"use client";

import { Landmark, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo } from "react";

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
import { ListPageTemplate } from "@/components/templates/list-page-template";
import { Button } from "@/components/ui/button";
import { getTenantColumns } from "@/features/platform/components/tenant-columns";
import { TENANT_STATUS_LABELS, TENANT_STATUS_OPTIONS } from "@/features/platform/constants/tenant-status";
import { useTenantFilters } from "@/features/platform/hooks/use-tenant-filters";
import { useTenants } from "@/features/platform/hooks/use-tenants";
import type { TenantFilters } from "@/features/platform/schemas/tenant-filters";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { normalizeApiError } from "@/utils/api-error";

/**
 * The Platform Tenants list — tenant lifecycle metadata and provisioning
 * only, never any tenant's business data (Sprint 17 Session 4's explicit
 * scope). All filter/page state lives in the URL via `useTenantFilters`,
 * mirroring `CompanyListPage`'s own rationale. No sort/city-style filter:
 * the backend's TenantListParams only supports `q`/`status`/pagination.
 */
export function PlatformTenantListPage() {
  const router = useRouter();
  const [filters, setFilters] = useTenantFilters();
  const [searchKey, reportSearch] = useExternalValueKey(filters.search);

  const listQuery = useTenants(filters);
  const tenants = listQuery.data?.data ?? [];
  const totalCount = listQuery.data?.meta.total_records ?? 0;
  const apiError = listQuery.isError ? normalizeApiError(listQuery.error) : null;

  const hasActiveFilters = Boolean(filters.search.trim() || filters.status);
  const isGenuinelyEmpty = !listQuery.isLoading && !apiError && totalCount === 0 && !hasActiveFilters;
  const isNoResults = !listQuery.isLoading && !apiError && totalCount === 0 && hasActiveFilters;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<TenantFilters, "page">>) => {
      setFilters({ ...patch, page: 1 });
    },
    [setFilters]
  );

  const goToPage = useCallback((page: number) => setFilters({ page }), [setFilters]);
  const setPageSize = useCallback((pageSize: number) => setFilters({ pageSize, page: 1 }), [setFilters]);
  const clearAllFilters = useCallback(() => setFilters(null), [setFilters]);

  // Same rationale as CompanyListPage: a filter change or the last row on
  // the last page disappearing can leave `filters.page` pointing past the
  // new last page — step back once a completed fetch confirms it's out of range.
  useEffect(() => {
    if (listQuery.isLoading || totalCount === 0) return;
    const lastPage = Math.max(1, Math.ceil(totalCount / filters.pageSize));
    if (filters.page > lastPage) goToPage(lastPage);
  }, [listQuery.isLoading, totalCount, filters.page, filters.pageSize, goToPage]);

  const columns = useMemo(() => getTenantColumns(), []);

  const table = useDataTable({
    data: tenants,
    columns,
    pageCount: Math.max(1, Math.ceil(totalCount / filters.pageSize)),
  });

  const appliedFilters: AppliedFilter[] = [
    filters.search.trim() ? { key: "search", label: `Search: "${filters.search.trim()}"` } : null,
    filters.status ? { key: "status", label: `Status: ${TENANT_STATUS_LABELS[filters.status]}` } : null,
  ].filter((filter): filter is AppliedFilter => filter !== null);

  function removeAppliedFilter(key: string) {
    if (key === "search") applyFilterChange({ search: "" });
    if (key === "status") applyFilterChange({ status: null });
  }

  return (
    <ListPageTemplate
      title="Platform Administration — Tenants"
      description="Provision tenants and manage their lifecycle status."
      icon={Landmark}
      primaryAction={{ label: "New Tenant", icon: Plus, href: "/platform/tenants/new" }}
      isLoading={listQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load tenants",
              description: apiError.message,
              onRetry: () => listQuery.refetch(),
            }
          : null
      }
      isEmpty={isGenuinelyEmpty}
      emptyState={
        <DataTableEmpty
          title="No tenants yet"
          description="Tenants you provision will appear here."
          action={
            <Button asChild size="sm">
              <Link href="/platform/tenants/new">
                <Plus aria-hidden />
                New Tenant
              </Link>
            </Button>
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
                  placeholder="Search by name or slug…"
                  isLoading={listQuery.isFetching}
                  aria-label="Search tenants"
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
                    options={TENANT_STATUS_OPTIONS}
                    value={filters.status ?? undefined}
                    onChange={(value) => applyFilterChange({ status: value ?? null })}
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
                ? `No tenants match "${filters.search.trim()}". Try a different search or clear your filters.`
                : "Try adjusting your search or filters."
            }
            onClearFilters={clearAllFilters}
          />
        }
        onRowClick={(tenant) => router.push(`/platform/tenants/${tenant.id}`)}
        stickyActionColumn
        aria-label="Tenants"
      />
    </ListPageTemplate>
  );
}
