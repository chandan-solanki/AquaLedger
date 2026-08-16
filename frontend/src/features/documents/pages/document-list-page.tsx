"use client";

import { format, parseISO } from "date-fns";
import { FolderOpen } from "lucide-react";
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
import { ListPageTemplate } from "@/components/templates/list-page-template";
import { getDocumentColumns } from "@/features/documents/components/document-columns";
import {
  DOCUMENT_PARTY_TYPE_LABELS,
  DOCUMENT_PARTY_TYPE_OPTIONS,
  DOCUMENT_TYPE_LABELS,
  DOCUMENT_TYPE_OPTIONS,
} from "@/features/documents/constants/document-type";
import { useDocumentFilters } from "@/features/documents/hooks/use-document-filters";
import { useDocuments } from "@/features/documents/hooks/use-documents";
import type { DocumentFilters } from "@/features/documents/schemas/document-filters";
import { triggerDocumentDownload } from "@/features/documents/utils/trigger-document-download";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { normalizeApiError } from "@/utils/api-error";
import { formatDate } from "@/utils/format-date";

const ISO_DATE_FORMAT = "yyyy-MM-dd";

function toDateRange(filters: DocumentFilters): DateRange | undefined {
  if (!filters.fromDate && !filters.toDate) return undefined;
  return {
    from: filters.fromDate ? parseISO(filters.fromDate) : undefined,
    to: filters.toDate ? parseISO(filters.toDate) : undefined,
  };
}

/**
 * The Document Center: a read-only, searchable/filterable/paginated history
 * of every business document (PDF) the system has generated — invoices,
 * purchase bills, customer/supplier payment receipts — for discovery and
 * re-download only. There is no create/edit/delete surface here (a document
 * record is only ever produced by its own module's render pipeline, never
 * authored here) and no Detail page (the backend exposes only
 * `GET /documents` and `GET /documents/{id}/download` — no
 * `GET /documents/{id}`), so rows have no `onRowClick` and the only
 * per-row action is Download. All filter/sort/page state lives in the URL
 * via `useDocumentFilters` (nuqs), mirroring `PaymentListPage` exactly.
 */
export function DocumentListPage() {
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = useDocumentFilters();
  const [searchKey, reportSearch] = useExternalValueKey(filters.search);

  const listQuery = useDocuments(filters);
  const documents = listQuery.data?.data ?? [];
  const totalCount = listQuery.data?.meta.total_records ?? 0;
  const apiError = listQuery.isError ? normalizeApiError(listQuery.error) : null;

  const hasActiveFilters = Boolean(
    filters.search.trim() || filters.documentType || filters.partyType || filters.fromDate || filters.toDate
  );
  const isGenuinelyEmpty = !listQuery.isLoading && !apiError && totalCount === 0 && !hasActiveFilters;
  const isNoResults = !listQuery.isLoading && !apiError && totalCount === 0 && hasActiveFilters;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<DocumentFilters, "page">>) => {
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
  // confirms it's out of range. Mirrors `PaymentListPage`.
  useEffect(() => {
    if (listQuery.isLoading || totalCount === 0) return;
    const lastPage = Math.max(1, Math.ceil(totalCount / filters.pageSize));
    if (filters.page > lastPage) goToPage(lastPage);
  }, [listQuery.isLoading, totalCount, filters.page, filters.pageSize, goToPage]);

  const dateRange = useMemo(() => toDateRange(filters), [filters]);

  const columns = useMemo(
    () => getDocumentColumns((document) => triggerDocumentDownload(document.id), hasPermission),
    [hasPermission]
  );

  const sorting = useMemo<SortingState>(
    () => [{ id: filters.sort, desc: filters.direction === "desc" }],
    [filters.sort, filters.direction]
  );

  const table = useDataTable({
    data: documents,
    columns,
    sorting,
    onSortingChange: (updater) => {
      const [next] = typeof updater === "function" ? updater(sorting) : updater;
      if (next) {
        applyFilterChange({ sort: next.id as DocumentFilters["sort"], direction: next.desc ? "desc" : "asc" });
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

  const dateRangeLabel = useMemo(() => {
    if (!filters.fromDate && !filters.toDate) return null;
    const from = filters.fromDate ? formatDate(filters.fromDate) : "…";
    const to = filters.toDate ? formatDate(filters.toDate) : "…";
    return `Generated: ${from} – ${to}`;
  }, [filters.fromDate, filters.toDate]);

  const appliedFilters: AppliedFilter[] = [
    filters.search.trim() ? { key: "search", label: `Search: "${filters.search.trim()}"` } : null,
    filters.documentType
      ? { key: "documentType", label: `Document: ${DOCUMENT_TYPE_LABELS[filters.documentType]}` }
      : null,
    filters.partyType
      ? { key: "partyType", label: `Party Type: ${DOCUMENT_PARTY_TYPE_LABELS[filters.partyType]}` }
      : null,
    dateRangeLabel ? { key: "dateRange", label: dateRangeLabel } : null,
  ].filter((filter): filter is AppliedFilter => filter !== null);

  function removeAppliedFilter(key: string) {
    if (key === "search") applyFilterChange({ search: "" });
    if (key === "documentType") applyFilterChange({ documentType: null });
    if (key === "partyType") applyFilterChange({ partyType: null });
    if (key === "dateRange") applyFilterChange({ fromDate: null, toDate: null });
  }

  return (
    <ListPageTemplate
      title="Document Center"
      description="View and download generated business documents"
      icon={FolderOpen}
      isLoading={listQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load documents",
              description: apiError.message,
              onRetry: () => listQuery.refetch(),
            }
          : null
      }
      isEmpty={isGenuinelyEmpty}
      emptyState={
        <DataTableEmpty
          title="No documents found"
          description="Generated invoices, purchase bills and payment receipts will appear here."
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
                  placeholder="Search by document number, party or file name…"
                  isLoading={listQuery.isFetching}
                  aria-label="Search documents"
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
                    label="Document Type"
                    options={DOCUMENT_TYPE_OPTIONS}
                    value={filters.documentType ?? undefined}
                    onChange={(value) => applyFilterChange({ documentType: value ?? null })}
                  />
                  <StatusFilter
                    label="Party Type"
                    options={DOCUMENT_PARTY_TYPE_OPTIONS}
                    value={filters.partyType ?? undefined}
                    onChange={(value) => applyFilterChange({ partyType: value ?? null })}
                  />
                  <DateRangeFilter
                    label="Generated Date"
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
            title="No documents found"
            description="Try changing your filters or search terms."
            onClearFilters={clearAllFilters}
          />
        }
        stickyActionColumn
        aria-label="Documents"
      />
    </ListPageTemplate>
  );
}
