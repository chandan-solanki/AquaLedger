"use client";

import { format, parseISO } from "date-fns";
import { History } from "lucide-react";
import { useCallback, useEffect, useMemo } from "react";
import type { SortingState } from "@tanstack/react-table";
import type { DateRange } from "react-day-picker";

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
import { ErrorState } from "@/components/feedback/error-state";
import { ListPageTemplate } from "@/components/templates/list-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { getAuditLogColumns } from "@/features/audit-logs/components/audit-log-columns";
import {
  AUDIT_LOG_ACTION_OPTIONS,
  AUDIT_LOG_ENTITY_TYPE_OPTIONS,
  humanizeAuditAction,
  humanizeAuditEntityType,
} from "@/features/audit-logs/constants/audit-log-action";
import { useActorOptions } from "@/features/audit-logs/hooks/use-actor-options";
import { useAuditLogFilters } from "@/features/audit-logs/hooks/use-audit-log-filters";
import { useAuditLogs } from "@/features/audit-logs/hooks/use-audit-logs";
import type { AuditLogFilters } from "@/features/audit-logs/schemas/audit-log-filters";
import { normalizeApiError } from "@/utils/api-error";
import { formatDate } from "@/utils/format-date";

const AUDIT_LOG_VIEW_PERMISSION = "audit_log:view";
const ISO_DATE_FORMAT = "yyyy-MM-dd";

function toDateRange(filters: AuditLogFilters): DateRange | undefined {
  if (!filters.fromDate && !filters.toDate) return undefined;
  return {
    from: filters.fromDate ? parseISO(filters.fromDate) : undefined,
    to: filters.toDate ? parseISO(filters.toDate) : undefined,
  };
}

/**
 * Administration -> Audit Logs: a read-only, searchable/filterable/
 * paginated history of administrative and security events (logins, and
 * every Users module create/update/status/role-change). There is no
 * create/edit/delete surface here and no Detail page - the backend exposes
 * only `GET /audit-logs` (list), no `GET /audit-logs/{id}` (every field is
 * already small enough to show inline - see the backend router's module
 * docstring), so rows have no `onRowClick`. Gated on `audit_log:view` - a
 * distinct permission from `user:manage` that the seed data already grants
 * to super_admin/admin/manager. Mirrors `DocumentListPage`'s structure
 * closely (also read-only, also server-paginated with a date-range filter).
 */
export function AuditLogListPage() {
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = useAuditLogFilters();

  const listQuery = useAuditLogs(filters);
  const actorOptionsQuery = useActorOptions();
  const auditLogs = listQuery.data?.data ?? [];
  const totalCount = listQuery.data?.meta.total_records ?? 0;
  const apiError = listQuery.isError ? normalizeApiError(listQuery.error) : null;

  const hasActiveFilters = Boolean(
    filters.search.trim() ||
      filters.action ||
      filters.entityType ||
      filters.userId ||
      filters.fromDate ||
      filters.toDate
  );
  const isGenuinelyEmpty = !listQuery.isLoading && !apiError && totalCount === 0 && !hasActiveFilters;
  const isNoResults = !listQuery.isLoading && !apiError && totalCount === 0 && hasActiveFilters;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<AuditLogFilters, "page">>) => {
      setFilters({ ...patch, page: 1 });
    },
    [setFilters]
  );

  const goToPage = useCallback((page: number) => setFilters({ page }), [setFilters]);
  const setPageSize = useCallback((pageSize: number) => setFilters({ pageSize, page: 1 }), [setFilters]);
  const clearAllFilters = useCallback(() => setFilters(null), [setFilters]);

  // Mirrors DocumentListPage: a filter change narrowing the result set can
  // leave `filters.page` pointing past the new last page.
  useEffect(() => {
    if (listQuery.isLoading || totalCount === 0) return;
    const lastPage = Math.max(1, Math.ceil(totalCount / filters.pageSize));
    if (filters.page > lastPage) goToPage(lastPage);
  }, [listQuery.isLoading, totalCount, filters.page, filters.pageSize, goToPage]);

  const dateRange = useMemo(() => toDateRange(filters), [filters]);

  const columns = useMemo(() => getAuditLogColumns(), []);

  const sorting = useMemo<SortingState>(
    () => [{ id: filters.sort, desc: filters.direction === "desc" }],
    [filters.sort, filters.direction]
  );

  const table = useDataTable({
    data: auditLogs,
    columns,
    sorting,
    onSortingChange: (updater) => {
      const [next] = typeof updater === "function" ? updater(sorting) : updater;
      if (next) {
        applyFilterChange({
          sort: next.id as AuditLogFilters["sort"],
          direction: next.desc ? "desc" : "asc",
        });
        return;
      }
      applyFilterChange({ direction: filters.direction === "desc" ? "asc" : "desc" });
    },
    enableMultiSort: false,
    pageCount: Math.max(1, Math.ceil(totalCount / filters.pageSize)),
  });

  const actorName = (userId: string | null) =>
    actorOptionsQuery.data?.data.find((user) => user.id === userId)?.fullName ?? userId ?? "";

  const dateRangeLabel = useMemo(() => {
    if (!filters.fromDate && !filters.toDate) return null;
    const from = filters.fromDate ? formatDate(filters.fromDate) : "…";
    const to = filters.toDate ? formatDate(filters.toDate) : "…";
    return `Date: ${from} – ${to}`;
  }, [filters.fromDate, filters.toDate]);

  const appliedFilters: AppliedFilter[] = [
    filters.search.trim() ? { key: "search", label: `Search: "${filters.search.trim()}"` } : null,
    filters.action ? { key: "action", label: `Action: ${humanizeAuditAction(filters.action)}` } : null,
    filters.entityType
      ? { key: "entityType", label: `Resource: ${humanizeAuditEntityType(filters.entityType)}` }
      : null,
    filters.userId ? { key: "userId", label: `User: ${actorName(filters.userId)}` } : null,
    dateRangeLabel ? { key: "dateRange", label: dateRangeLabel } : null,
  ].filter((filter): filter is AppliedFilter => filter !== null);

  function removeAppliedFilter(key: string) {
    if (key === "search") applyFilterChange({ search: "" });
    if (key === "action") applyFilterChange({ action: null });
    if (key === "entityType") applyFilterChange({ entityType: null });
    if (key === "userId") applyFilterChange({ userId: null });
    if (key === "dateRange") applyFilterChange({ fromDate: null, toDate: null });
  }

  // Every hook above must run unconditionally on every render - this check
  // comes after all of them, not before, so it can safely early-return.
  if (!hasPermission(AUDIT_LOG_VIEW_PERMISSION)) {
    return (
      <ErrorState
        title="You don't have permission to view audit logs"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  return (
    <ListPageTemplate
      title="Audit Logs"
      description="A history of administrative and security events for your organization."
      icon={History}
      isLoading={listQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load audit logs",
              description: apiError.message,
              onRetry: () => listQuery.refetch(),
            }
          : null
      }
      isEmpty={isGenuinelyEmpty}
      emptyState={
        <DataTableEmpty
          title="No audit records yet"
          description="Administrative and security events will appear here as they happen."
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
                  defaultValue={filters.search}
                  onSearch={(value) => applyFilterChange({ search: value })}
                  placeholder="Search by user name or email…"
                  isLoading={listQuery.isFetching}
                  aria-label="Search audit logs"
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
                    label="Action"
                    options={AUDIT_LOG_ACTION_OPTIONS}
                    value={filters.action ?? undefined}
                    onChange={(value) => applyFilterChange({ action: value ?? null })}
                  />
                  <StatusFilter
                    label="Resource"
                    options={AUDIT_LOG_ENTITY_TYPE_OPTIONS}
                    value={filters.entityType ?? undefined}
                    onChange={(value) => applyFilterChange({ entityType: value ?? null })}
                  />
                  <StatusFilter
                    label="User"
                    options={(actorOptionsQuery.data?.data ?? []).map((user) => ({
                      value: user.id,
                      label: user.fullName,
                    }))}
                    value={filters.userId ?? undefined}
                    onChange={(value) => applyFilterChange({ userId: value ?? null })}
                  />
                  <DateRangeFilter
                    label="Date"
                    value={dateRange}
                    onChange={(range) =>
                      applyFilterChange({
                        fromDate: range?.from ? format(range.from, ISO_DATE_FORMAT) : null,
                        toDate: range?.to ? format(range.to, ISO_DATE_FORMAT) : null,
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
            description="Try changing your filters or search terms."
            onClearFilters={clearAllFilters}
          />
        }
        aria-label="Audit Logs"
      />
    </ListPageTemplate>
  );
}
