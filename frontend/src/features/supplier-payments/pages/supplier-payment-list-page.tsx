"use client";

import { ArrowUpFromLine, Plus } from "lucide-react";
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
import { getSupplierPaymentColumns } from "@/features/supplier-payments/components/supplier-payment-columns";
import { useSupplierPaymentRowActions } from "@/features/supplier-payments/components/supplier-payment-row-actions";
import {
  SUPPLIER_PAYMENT_METHOD_LABELS,
  SUPPLIER_PAYMENT_METHOD_OPTIONS,
} from "@/features/supplier-payments/constants/supplier-payment-method";
import {
  SUPPLIER_PAYMENT_STATUS_LABELS,
  SUPPLIER_PAYMENT_STATUS_OPTIONS,
} from "@/features/supplier-payments/constants/supplier-payment-status";
import { useDeleteSupplierPayment } from "@/features/supplier-payments/hooks/use-delete-supplier-payment";
import { useSupplierOptions } from "@/features/supplier-payments/hooks/use-supplier-options";
import { useSupplierPaymentFilters } from "@/features/supplier-payments/hooks/use-supplier-payment-filters";
import { useSupplierPayments } from "@/features/supplier-payments/hooks/use-supplier-payments";
import type { SupplierPaymentFilters } from "@/features/supplier-payments/schemas/supplier-payment-filters";
import type { SupplierPayment } from "@/features/supplier-payments/types/supplier-payment";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { normalizeApiError } from "@/utils/api-error";

/**
 * The Supplier Payment list page: API integration, search, filters, sorting,
 * pagination, the "New Supplier Payment" entry point, row click navigation
 * and row-level View/Edit/Delete (Sprint 9 Sessions 1-4, see TASKS.md).
 * There is no Post row action - posting lives on the Supplier Payment Detail
 * page only (`SupplierPaymentDetailPage`), mirroring how Payment's own Post
 * action is Detail-page-only. Delete is draft-only
 * (`useSupplierPaymentRowActions` hides it for any other status, mirroring
 * the Detail page's own gating) and reuses the shared
 * `DeleteConfirmationDialog` + `useDeleteSupplierPayment`, mirroring
 * `PaymentListPage` exactly. All filter/sort/page state lives in the URL via
 * `useSupplierPaymentFilters` (nuqs) - a refresh, a shared link, or Back/
 * Forward all restore the exact same list state, per ARCHITECTURE.md §10.
 */
export function SupplierPaymentListPage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = useSupplierPaymentFilters();
  const [searchKey, reportSearch] = useExternalValueKey(filters.search);
  const [pendingDelete, setPendingDelete] = useState<SupplierPayment | null>(null);

  const listQuery = useSupplierPayments(filters);
  const supplierOptions = useSupplierOptions();
  const deleteSupplierPayment = useDeleteSupplierPayment();
  const supplierPayments = listQuery.data?.data ?? [];
  const totalCount = listQuery.data?.meta.total_records ?? 0;
  const apiError = listQuery.isError ? normalizeApiError(listQuery.error) : null;

  const hasActiveFilters = Boolean(
    filters.search.trim() || filters.status || filters.supplier || filters.method
  );
  const isGenuinelyEmpty = !listQuery.isLoading && !apiError && totalCount === 0 && !hasActiveFilters;
  const isNoResults = !listQuery.isLoading && !apiError && totalCount === 0 && hasActiveFilters;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<SupplierPaymentFilters, "page">>) => {
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

  const onDeleteRequest = useCallback((payment: SupplierPayment) => setPendingDelete(payment), []);
  const rowActionsFor = useSupplierPaymentRowActions(onDeleteRequest);
  const columns = useMemo(
    () => getSupplierPaymentColumns(rowActionsFor, supplierOptions.nameById),
    [rowActionsFor, supplierOptions.nameById]
  );

  const sorting = useMemo<SortingState>(
    () => [{ id: filters.sort, desc: filters.direction === "desc" }],
    [filters.sort, filters.direction]
  );

  const table = useDataTable({
    data: supplierPayments,
    columns,
    sorting,
    onSortingChange: (updater) => {
      const [next] = typeof updater === "function" ? updater(sorting) : updater;
      if (next) {
        applyFilterChange({
          sort: next.id as SupplierPaymentFilters["sort"],
          direction: next.desc ? "desc" : "asc",
        });
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
    filters.status
      ? { key: "status", label: `Status: ${SUPPLIER_PAYMENT_STATUS_LABELS[filters.status]}` }
      : null,
    filters.supplier
      ? {
          key: "supplier",
          label: `Supplier: ${supplierOptions.nameById.get(filters.supplier) ?? filters.supplier}`,
        }
      : null,
    filters.method
      ? { key: "method", label: `Method: ${SUPPLIER_PAYMENT_METHOD_LABELS[filters.method]}` }
      : null,
  ].filter((filter): filter is AppliedFilter => filter !== null);

  function removeAppliedFilter(key: string) {
    if (key === "search") applyFilterChange({ search: "" });
    if (key === "status") applyFilterChange({ status: null });
    if (key === "supplier") applyFilterChange({ supplier: null });
    if (key === "method") applyFilterChange({ method: null });
  }

  return (
    <>
      <ListPageTemplate
        title="Supplier Payments"
        description="Payments made to your suppliers."
        icon={ArrowUpFromLine}
        primaryAction={
          hasPermission("supplier_payment:create")
            ? { label: "New Supplier Payment", icon: Plus, href: "/supplier-payments/new" }
            : undefined
        }
        isLoading={listQuery.isLoading}
        error={
          apiError
            ? {
                title: "Failed to load supplier payments",
                description: apiError.message,
                onRetry: () => listQuery.refetch(),
              }
            : null
        }
        isEmpty={isGenuinelyEmpty}
        emptyState={
          <DataTableEmpty
            title="No supplier payments yet"
            description="Supplier payments you record will appear here."
            action={
              hasPermission("supplier_payment:create") ? (
                <Button asChild size="sm">
                  <Link href="/supplier-payments/new">
                    <Plus aria-hidden />
                    New Supplier Payment
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
                    aria-label="Search supplier payments"
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
                      options={SUPPLIER_PAYMENT_STATUS_OPTIONS}
                      value={filters.status ?? undefined}
                      onChange={(value) => applyFilterChange({ status: value ?? null })}
                    />
                    <SearchableSelect
                      label="Supplier"
                      placeholder="All suppliers"
                      options={supplierOptions.options}
                      value={filters.supplier ?? undefined}
                      onChange={(value) => applyFilterChange({ supplier: value ?? null })}
                    />
                    <StatusFilter
                      label="Payment Method"
                      options={SUPPLIER_PAYMENT_METHOD_OPTIONS}
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
                  ? `No supplier payments match "${filters.search.trim()}". Try a different search or clear your filters.`
                  : "Try adjusting your search or filters."
              }
              onClearFilters={clearAllFilters}
            />
          }
          onRowClick={
            hasPermission("supplier_payment:view")
              ? (payment) => router.push(`/supplier-payments/${payment.id}`)
              : undefined
          }
          stickyActionColumn
          aria-label="Supplier Payments"
        />
      </ListPageTemplate>

      {pendingDelete && (
        <DeleteConfirmationDialog
          open={Boolean(pendingDelete)}
          onOpenChange={(open) => !open && setPendingDelete(null)}
          entityName={pendingDelete.paymentNumber ?? "this draft supplier payment"}
          entityLabel="supplier payment"
          isLoading={deleteSupplierPayment.isPending}
          onConfirm={() =>
            deleteSupplierPayment.mutate(pendingDelete.id, { onSuccess: () => setPendingDelete(null) })
          }
        />
      )}
    </>
  );
}
