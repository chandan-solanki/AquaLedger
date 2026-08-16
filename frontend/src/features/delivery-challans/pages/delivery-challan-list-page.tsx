"use client";

import { format, parseISO } from "date-fns";
import { Plus, Truck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo } from "react";
import type { DateRange } from "react-day-picker";
import type { SortingState } from "@tanstack/react-table";

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
import { SearchableSelect } from "@/components/form";
import { ListPageTemplate } from "@/components/templates/list-page-template";
import { Button } from "@/components/ui/button";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { getDeliveryChallanColumns } from "@/features/delivery-challans/components/delivery-challan-columns";
import { useDeliveryChallanRowActions } from "@/features/delivery-challans/components/delivery-challan-row-actions";
import {
  DELIVERY_CHALLAN_STATUS_LABELS,
  DELIVERY_CHALLAN_STATUS_OPTIONS,
} from "@/features/delivery-challans/constants/delivery-challan-status";
import { useDeliveryChallanFilters } from "@/features/delivery-challans/hooks/use-delivery-challan-filters";
import { useDeliveryChallans } from "@/features/delivery-challans/hooks/use-delivery-challans";
import { useInvoiceOptions } from "@/features/delivery-challans/hooks/use-invoice-options";
import type { DeliveryChallanFilters } from "@/features/delivery-challans/schemas/delivery-challan-filters";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { normalizeApiError } from "@/utils/api-error";

function toDateRange(from: string | null, to: string | null): DateRange | undefined {
  if (!from && !to) return undefined;
  return {
    from: from ? parseISO(from) : undefined,
    to: to ? parseISO(to) : undefined,
  };
}

function toIsoDateOrNull(date: Date | undefined): string | null {
  return date ? format(date, "yyyy-MM-dd") : null;
}

/**
 * The Delivery Challans list page: API integration, search, filters,
 * sorting, pagination, the "New Delivery Challan" entry point, row
 * navigation, and row-level View/Edit, mirroring `PurchaseOrderListPage`.
 * All filter/sort/page state lives in the URL via
 * `useDeliveryChallanFilters` (nuqs) - a refresh, a shared link, or
 * Back/Forward all restore the exact same list state, per
 * ARCHITECTURE.md §10.
 *
 * There is deliberately no Customer filter - the backend's own
 * `DeliveryChallanListParams` exposes no company/customer filter (the
 * customer is only ever reachable via the linked invoice), so this list
 * only ever filters by Invoice.
 */
export function DeliveryChallanListPage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = useDeliveryChallanFilters();
  const [searchKey, reportSearch] = useExternalValueKey(filters.search);

  const listQuery = useDeliveryChallans(filters);
  const invoiceOptions = useInvoiceOptions();
  const deliveryChallans = listQuery.data?.data ?? [];
  const totalCount = listQuery.data?.meta.total_records ?? 0;
  const apiError = listQuery.isError ? normalizeApiError(listQuery.error) : null;

  const hasActiveFilters = Boolean(
    filters.search.trim() || filters.status || filters.invoice || filters.challanDateFrom || filters.challanDateTo
  );
  const isGenuinelyEmpty = !listQuery.isLoading && !apiError && totalCount === 0 && !hasActiveFilters;
  const isNoResults = !listQuery.isLoading && !apiError && totalCount === 0 && hasActiveFilters;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<DeliveryChallanFilters, "page">>) => {
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

  const rowActionsFor = useDeliveryChallanRowActions();
  const columns = useMemo(
    () => getDeliveryChallanColumns(rowActionsFor, invoiceOptions.invoiceById, invoiceOptions.companyNameById),
    [rowActionsFor, invoiceOptions.invoiceById, invoiceOptions.companyNameById]
  );

  const sorting = useMemo<SortingState>(
    () => [{ id: filters.sort, desc: filters.direction === "desc" }],
    [filters.sort, filters.direction]
  );

  const table = useDataTable({
    data: deliveryChallans,
    columns,
    sorting,
    onSortingChange: (updater) => {
      const [next] = typeof updater === "function" ? updater(sorting) : updater;
      if (next) {
        applyFilterChange({
          sort: next.id as DeliveryChallanFilters["sort"],
          direction: next.desc ? "desc" : "asc",
        });
        return;
      }
      applyFilterChange({ direction: filters.direction === "desc" ? "asc" : "desc" });
    },
    enableMultiSort: false,
    pageCount: Math.max(1, Math.ceil(totalCount / filters.pageSize)),
  });

  const appliedFilters: AppliedFilter[] = [
    filters.search.trim() ? { key: "search", label: `Search: "${filters.search.trim()}"` } : null,
    filters.status
      ? { key: "status", label: `Status: ${DELIVERY_CHALLAN_STATUS_LABELS[filters.status]}` }
      : null,
    filters.invoice
      ? {
          key: "invoice",
          label: `Invoice: ${invoiceOptions.invoiceById.get(filters.invoice)?.invoiceNumber ?? filters.invoice}`,
        }
      : null,
    filters.challanDateFrom || filters.challanDateTo
      ? {
          key: "challanDate",
          label: `Challan Date: ${filters.challanDateFrom ?? "…"} – ${filters.challanDateTo ?? "…"}`,
        }
      : null,
  ].filter((filter): filter is AppliedFilter => filter !== null);

  function removeAppliedFilter(key: string) {
    if (key === "search") applyFilterChange({ search: "" });
    if (key === "status") applyFilterChange({ status: null });
    if (key === "invoice") applyFilterChange({ invoice: null });
    if (key === "challanDate") applyFilterChange({ challanDateFrom: null, challanDateTo: null });
  }

  return (
    <ListPageTemplate
      title="Delivery Challans"
      description="Physical dispatch and delivery of goods already invoiced to customers."
      icon={Truck}
      primaryAction={
        hasPermission("delivery_challan:create")
          ? { label: "New Delivery Challan", icon: Plus, href: "/delivery-challans/new" }
          : undefined
      }
      isLoading={listQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load delivery challans",
              description: apiError.message,
              onRetry: () => listQuery.refetch(),
            }
          : null
      }
      isEmpty={isGenuinelyEmpty}
      emptyState={
        <DataTableEmpty
          title="No delivery challans yet"
          description="Deliveries dispatched against your invoices will appear here."
          action={
            hasPermission("delivery_challan:create") ? (
              <Button asChild size="sm">
                <Link href="/delivery-challans/new">
                  <Plus aria-hidden />
                  New Delivery Challan
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
                  placeholder="Search by challan number…"
                  isLoading={listQuery.isFetching}
                  aria-label="Search delivery challans"
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
                    options={DELIVERY_CHALLAN_STATUS_OPTIONS}
                    value={filters.status ?? undefined}
                    onChange={(value) => applyFilterChange({ status: value ?? null })}
                  />
                  <SearchableSelect
                    label="Invoice"
                    placeholder="All invoices"
                    options={invoiceOptions.eligibleOptions}
                    value={filters.invoice ?? undefined}
                    onChange={(value) => applyFilterChange({ invoice: value ?? null })}
                  />
                  <DateRangeFilter
                    label="Challan Date"
                    value={toDateRange(filters.challanDateFrom, filters.challanDateTo)}
                    onChange={(range) =>
                      applyFilterChange({
                        challanDateFrom: toIsoDateOrNull(range?.from),
                        challanDateTo: toIsoDateOrNull(range?.to),
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
            description={
              filters.search.trim()
                ? `No delivery challans match "${filters.search.trim()}". Try a different search or clear your filters.`
                : "Try adjusting your search or filters."
            }
            onClearFilters={clearAllFilters}
          />
        }
        onRowClick={
          hasPermission("delivery_challan:view")
            ? (challan) => router.push(`/delivery-challans/${challan.id}`)
            : undefined
        }
        stickyActionColumn
        aria-label="Delivery Challans"
      />
    </ListPageTemplate>
  );
}
