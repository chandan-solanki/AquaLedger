"use client";

import { ArrowDownToLine, Plus } from "lucide-react";
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
import { getPaymentColumns } from "@/features/payments/components/payment-columns";
import { usePaymentRowActions } from "@/features/payments/components/payment-row-actions";
import { PAYMENT_METHOD_LABELS, PAYMENT_METHOD_OPTIONS } from "@/features/payments/constants/payment-method";
import { PAYMENT_STATUS_LABELS, PAYMENT_STATUS_OPTIONS } from "@/features/payments/constants/payment-status";
import { useCompanyOptions } from "@/features/payments/hooks/use-company-options";
import { useDeletePayment } from "@/features/payments/hooks/use-delete-payment";
import { usePaymentFilters } from "@/features/payments/hooks/use-payment-filters";
import { usePayments } from "@/features/payments/hooks/use-payments";
import type { PaymentFilters } from "@/features/payments/schemas/payment-filters";
import type { Payment } from "@/features/payments/types/payment";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { normalizeApiError } from "@/utils/api-error";

/**
 * The Payment list page: API integration, search, filters, sorting,
 * pagination, the "New Payment" entry point, row click navigation and row-
 * level View/Edit/Delete - Sprint 8 Sessions 2-4's scope (see TASKS.md).
 * There is no Allocate/Post row action - allocation management and posting
 * both live on the Payment Detail page only (`PaymentDetailPage`), mirroring
 * how Invoice's Issue action is Detail-page-only. Delete is draft-only
 * (`usePaymentRowActions` hides it for any other status, mirroring the
 * Detail page's own gating) and reuses the shared `DeleteConfirmationDialog`
 * + `useDeletePayment`, mirroring `InvoiceListPage` exactly. All filter/
 * sort/page state lives in the URL via `usePaymentFilters` (nuqs) - a
 * refresh, a shared link, or Back/Forward all restore the exact same list
 * state, per ARCHITECTURE.md §10.
 */
export function PaymentListPage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = usePaymentFilters();
  const [searchKey, reportSearch] = useExternalValueKey(filters.search);
  const [pendingDelete, setPendingDelete] = useState<Payment | null>(null);

  const listQuery = usePayments(filters);
  const companyOptions = useCompanyOptions();
  const deletePayment = useDeletePayment();
  const payments = listQuery.data?.data ?? [];
  const totalCount = listQuery.data?.meta.total_records ?? 0;
  const apiError = listQuery.isError ? normalizeApiError(listQuery.error) : null;

  const hasActiveFilters = Boolean(
    filters.search.trim() || filters.status || filters.company || filters.method
  );
  const isGenuinelyEmpty = !listQuery.isLoading && !apiError && totalCount === 0 && !hasActiveFilters;
  const isNoResults = !listQuery.isLoading && !apiError && totalCount === 0 && hasActiveFilters;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<PaymentFilters, "page">>) => {
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

  const onDeleteRequest = useCallback((payment: Payment) => setPendingDelete(payment), []);
  const rowActionsFor = usePaymentRowActions(onDeleteRequest);
  const columns = useMemo(
    () => getPaymentColumns(rowActionsFor, companyOptions.nameById),
    [rowActionsFor, companyOptions.nameById]
  );

  const sorting = useMemo<SortingState>(
    () => [{ id: filters.sort, desc: filters.direction === "desc" }],
    [filters.sort, filters.direction]
  );

  const table = useDataTable({
    data: payments,
    columns,
    sorting,
    onSortingChange: (updater) => {
      const [next] = typeof updater === "function" ? updater(sorting) : updater;
      if (next) {
        applyFilterChange({ sort: next.id as PaymentFilters["sort"], direction: next.desc ? "desc" : "asc" });
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
    filters.status ? { key: "status", label: `Status: ${PAYMENT_STATUS_LABELS[filters.status]}` } : null,
    filters.company
      ? { key: "company", label: `Customer: ${companyOptions.nameById.get(filters.company) ?? filters.company}` }
      : null,
    filters.method ? { key: "method", label: `Method: ${PAYMENT_METHOD_LABELS[filters.method]}` } : null,
  ].filter((filter): filter is AppliedFilter => filter !== null);

  function removeAppliedFilter(key: string) {
    if (key === "search") applyFilterChange({ search: "" });
    if (key === "status") applyFilterChange({ status: null });
    if (key === "company") applyFilterChange({ company: null });
    if (key === "method") applyFilterChange({ method: null });
  }

  return (
    <>
      <ListPageTemplate
        title="Customer Payments"
        description="Payments received from your companies."
        icon={ArrowDownToLine}
        primaryAction={
          hasPermission("payment:create") ? { label: "New Payment", icon: Plus, href: "/payments/new" } : undefined
        }
        isLoading={listQuery.isLoading}
        error={
          apiError
            ? {
                title: "Failed to load payments",
                description: apiError.message,
                onRetry: () => listQuery.refetch(),
              }
            : null
        }
        isEmpty={isGenuinelyEmpty}
        emptyState={
          <DataTableEmpty
            title="No payments yet"
            description="Payments you record will appear here."
            action={
              hasPermission("payment:create") ? (
                <Button asChild size="sm">
                  <Link href="/payments/new">
                    <Plus aria-hidden />
                    New Payment
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
                    placeholder="Search by payment number or reference…"
                    isLoading={listQuery.isFetching}
                    aria-label="Search payments"
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
                      options={PAYMENT_STATUS_OPTIONS}
                      value={filters.status ?? undefined}
                      onChange={(value) => applyFilterChange({ status: value ?? null })}
                    />
                    <SearchableSelect
                      label="Customer"
                      placeholder="All customers"
                      options={companyOptions.options}
                      value={filters.company ?? undefined}
                      onChange={(value) => applyFilterChange({ company: value ?? null })}
                    />
                    <StatusFilter
                      label="Payment Method"
                      options={PAYMENT_METHOD_OPTIONS}
                      value={filters.method ?? undefined}
                      onChange={(value) => applyFilterChange({ method: value ?? null })}
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
                  ? `No payments match "${filters.search.trim()}". Try a different search or clear your filters.`
                  : "Try adjusting your search or filters."
              }
              onClearFilters={clearAllFilters}
            />
          }
          onRowClick={hasPermission("payment:view") ? (payment) => router.push(`/payments/${payment.id}`) : undefined}
          stickyActionColumn
          aria-label="Payments"
        />
      </ListPageTemplate>

      {pendingDelete && (
        <DeleteConfirmationDialog
          open={Boolean(pendingDelete)}
          onOpenChange={(open) => !open && setPendingDelete(null)}
          entityName={pendingDelete.paymentNumber ?? "this draft payment"}
          entityLabel="payment"
          isLoading={deletePayment.isPending}
          onConfirm={() => deletePayment.mutate(pendingDelete.id, { onSuccess: () => setPendingDelete(null) })}
        />
      )}
    </>
  );
}
