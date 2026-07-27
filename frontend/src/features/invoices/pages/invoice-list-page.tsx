"use client";

import { FileText, Plus } from "lucide-react";
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
import { AdvancedFilter, AppliedFilters, SearchBar, StatusFilter } from "@/components/filters";
import type { AppliedFilter } from "@/components/filters";
import { DeleteConfirmationDialog } from "@/components/feedback/dialogs/delete-confirmation-dialog";
import { SearchableSelect } from "@/components/form";
import { ListPageTemplate } from "@/components/templates/list-page-template";
import { Button } from "@/components/ui/button";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { getInvoiceColumns } from "@/features/invoices/components/invoice-columns";
import { useInvoiceRowActions } from "@/features/invoices/components/invoice-row-actions";
import { INVOICE_STATUS_LABELS, INVOICE_STATUS_OPTIONS } from "@/features/invoices/constants/invoice-status";
import { useCompanyOptions } from "@/features/invoices/hooks/use-company-options";
import { useDeleteInvoice } from "@/features/invoices/hooks/use-delete-invoice";
import { useInvoiceFilters } from "@/features/invoices/hooks/use-invoice-filters";
import { useInvoices } from "@/features/invoices/hooks/use-invoices";
import type { InvoiceFilters } from "@/features/invoices/schemas/invoice-filters";
import type { Invoice } from "@/features/invoices/types/invoice";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { normalizeApiError } from "@/utils/api-error";

/**
 * The Invoice list page: API integration, search, filters, sorting,
 * pagination, the "New Invoice" entry point, row navigation, and row-level
 * View/Edit/Delete — Sprint 7 Session 4's scope (see TASKS.md). Row-click
 * navigates to `/invoices/{id}` (permission-gated on `invoice:view`). Delete
 * is draft-only (`useInvoiceRowActions` hides it for any other status,
 * mirroring the Detail page's own gating) and reuses the shared
 * `DeleteConfirmationDialog` + `useDeleteInvoice`, mirroring
 * `BoatListPage`/`CompanyListPage` exactly. All filter/sort/page state
 * lives in the URL via `useInvoiceFilters` (nuqs) — a refresh, a shared
 * link, or Back/Forward all restore the exact same list state, per
 * ARCHITECTURE.md §10, mirroring `TripListPage`'s architecture exactly.
 */
export function InvoiceListPage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = useInvoiceFilters();
  const [searchKey, reportSearch] = useExternalValueKey(filters.search);
  const [pendingDelete, setPendingDelete] = useState<Invoice | null>(null);

  const listQuery = useInvoices(filters);
  const companyOptions = useCompanyOptions();
  const deleteInvoice = useDeleteInvoice();
  const invoices = listQuery.data?.data ?? [];
  const totalCount = listQuery.data?.meta.total_records ?? 0;
  const apiError = listQuery.isError ? normalizeApiError(listQuery.error) : null;

  const hasActiveFilters = Boolean(filters.search.trim() || filters.status || filters.company);
  const isGenuinelyEmpty = !listQuery.isLoading && !apiError && totalCount === 0 && !hasActiveFilters;
  const isNoResults = !listQuery.isLoading && !apiError && totalCount === 0 && hasActiveFilters;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<InvoiceFilters, "page">>) => {
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

  const onDeleteRequest = useCallback((invoice: Invoice) => setPendingDelete(invoice), []);
  const rowActionsFor = useInvoiceRowActions(onDeleteRequest);
  const columns = useMemo(
    () => getInvoiceColumns(rowActionsFor, companyOptions.nameById),
    [rowActionsFor, companyOptions.nameById]
  );

  const sorting = useMemo<SortingState>(
    () => [{ id: filters.sort, desc: filters.direction === "desc" }],
    [filters.sort, filters.direction]
  );

  const table = useDataTable({
    data: invoices,
    columns,
    sorting,
    onSortingChange: (updater) => {
      const [next] = typeof updater === "function" ? updater(sorting) : updater;
      if (next) {
        applyFilterChange({ sort: next.id as InvoiceFilters["sort"], direction: next.desc ? "desc" : "asc" });
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
    filters.status ? { key: "status", label: `Status: ${INVOICE_STATUS_LABELS[filters.status]}` } : null,
    filters.company
      ? { key: "company", label: `Company: ${companyOptions.nameById.get(filters.company) ?? filters.company}` }
      : null,
  ].filter((filter): filter is AppliedFilter => filter !== null);

  function removeAppliedFilter(key: string) {
    if (key === "search") applyFilterChange({ search: "" });
    if (key === "status") applyFilterChange({ status: null });
    if (key === "company") applyFilterChange({ company: null });
  }

  return (
    <>
      <ListPageTemplate
        title="Invoices"
        description="Sales invoices billed to your companies."
        icon={FileText}
        primaryAction={
          hasPermission("invoice:create") ? { label: "New Invoice", icon: Plus, href: "/invoices/new" } : undefined
        }
        isLoading={listQuery.isLoading}
        error={
          apiError
            ? {
                title: "Failed to load invoices",
                description: apiError.message,
                onRetry: () => listQuery.refetch(),
              }
            : null
        }
        isEmpty={isGenuinelyEmpty}
        emptyState={
          <DataTableEmpty
            title="No invoices yet"
            description="Invoices you create will appear here."
            action={
              hasPermission("invoice:create") ? (
                <Button asChild size="sm">
                  <Link href="/invoices/new">
                    <Plus aria-hidden />
                    New Invoice
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
                    placeholder="Search by invoice number or company name…"
                    isLoading={listQuery.isFetching}
                    aria-label="Search invoices"
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
                      options={INVOICE_STATUS_OPTIONS}
                      value={filters.status ?? undefined}
                      onChange={(value) => applyFilterChange({ status: value ?? null })}
                    />
                    <SearchableSelect
                      label="Company"
                      placeholder="All companies"
                      options={companyOptions.options}
                      value={filters.company ?? undefined}
                      onChange={(value) => applyFilterChange({ company: value ?? null })}
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
                  ? `No invoices match "${filters.search.trim()}". Try a different search or clear your filters.`
                  : "Try adjusting your search or filters."
              }
              onClearFilters={clearAllFilters}
            />
          }
          onRowClick={hasPermission("invoice:view") ? (invoice) => router.push(`/invoices/${invoice.id}`) : undefined}
          stickyActionColumn
          aria-label="Invoices"
        />
      </ListPageTemplate>

      {pendingDelete && (
        <DeleteConfirmationDialog
          open={Boolean(pendingDelete)}
          onOpenChange={(open) => !open && setPendingDelete(null)}
          entityName={pendingDelete.invoiceNumber ?? "this draft invoice"}
          entityLabel="invoice"
          isLoading={deleteInvoice.isPending}
          onConfirm={() => deleteInvoice.mutate(pendingDelete.id, { onSuccess: () => setPendingDelete(null) })}
        />
      )}
    </>
  );
}
