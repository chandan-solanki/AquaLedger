"use client";

import { format, parseISO } from "date-fns";
import { useRouter } from "next/navigation";
import { X } from "lucide-react";
import { useCallback, useMemo } from "react";
import type { DateRange } from "react-day-picker";

import {
  DataTable,
  DataTableEmpty,
  DataTableNoResults,
  DataTablePagination,
  useDataTable,
} from "@/components/data-table";
import { DateRangeFilter, SearchBar, StatusFilter } from "@/components/filters";
import { SearchableSelect } from "@/components/form";
import { PageContainer } from "@/components/layout/page-container";
import { ExportMenu } from "@/components/reports";
import { ReportPageTemplate } from "@/components/templates/report-page-template";
import { Button } from "@/components/ui/button";
import { Forbidden } from "@/components/feedback/error-states";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { PurchaseReportSummaryCards } from "@/features/reports/components/purchase-report-summary-cards";
import { getPurchaseReportColumns } from "@/features/reports/components/purchase-report-columns";
import { PAID_STATUS_OPTIONS } from "@/features/reports/constants/paid-status";
import { usePurchaseReport } from "@/features/reports/hooks/use-purchase-report";
import { usePurchaseReportFilters } from "@/features/reports/hooks/use-purchase-report-filters";
import { useSupplierOptions } from "@/features/reports/hooks/use-supplier-options";
import {
  toPurchaseReportParams,
  type PurchaseReportFilters,
} from "@/features/reports/schemas/purchase-report-filters";
import type {
  PurchaseReportBillStatus,
  PurchaseReportRow,
} from "@/features/reports/types/purchase-report";
import { triggerReportDownload } from "@/features/reports/utils/trigger-report-download";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { normalizeApiError } from "@/utils/api-error";

const STATUS_OPTIONS: { value: PurchaseReportBillStatus; label: string }[] = [
  { value: "posted", label: "Posted" },
  { value: "partially_paid", label: "Partially Paid" },
  { value: "paid", label: "Paid" },
  { value: "cancelled", label: "Cancelled" },
];

function toDateRange(filters: PurchaseReportFilters): DateRange | undefined {
  if (!filters.fromDate && !filters.toDate) return undefined;
  return {
    from: filters.fromDate ? parseISO(filters.fromDate) : undefined,
    to: filters.toDate ? parseISO(filters.toDate) : undefined,
  };
}

const ISO_DATE_FORMAT = "yyyy-MM-dd";

/**
 * The Purchase Report page (TASKS.md Sprint 11 Session 3) - mirrors
 * `SalesReportPage` exactly, on the buy side. Clicking a row navigates to
 * the existing Purchase Bill Detail page, gated on `purchase:view`.
 */
export function PurchaseReportPage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = usePurchaseReportFilters();
  const [searchKey, reportSearch] = useExternalValueKey(filters.search);
  const supplierOptions = useSupplierOptions();
  const query = usePurchaseReport(filters);

  const data = query.data;
  const apiError = query.isError ? normalizeApiError(query.error) : null;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<PurchaseReportFilters, "page">>) => {
      setFilters({ ...patch, page: 1 });
    },
    [setFilters]
  );
  const goToPage = useCallback((page: number) => setFilters({ page }), [setFilters]);
  const setPageSize = useCallback(
    (pageSize: number) => setFilters({ pageSize, page: 1 }),
    [setFilters]
  );
  const resetFilters = useCallback(() => setFilters(null), [setFilters]);

  const dateRange = useMemo(() => toDateRange(filters), [filters]);
  const hasActiveFilters = Boolean(
    filters.search.trim() ||
      filters.supplierId ||
      filters.status ||
      filters.paidStatus ||
      filters.fromDate ||
      filters.toDate
  );

  const rows = useMemo(() => data?.rows ?? [], [data]);
  const columns = useMemo(() => getPurchaseReportColumns(), []);
  const table = useDataTable({
    data: rows,
    columns,
    pageCount: Math.max(1, Math.ceil((data?.pagination.totalRecords ?? 0) / filters.pageSize)),
  });

  if (apiError?.category === "forbidden") {
    return (
      <PageContainer>
        <Forbidden description="You don't have permission to view accounting reports. Contact an administrator if you believe this is a mistake." />
      </PageContainer>
    );
  }

  const filterBar = (
    <div className="flex flex-wrap items-end gap-3">
      <SearchBar
        key={searchKey}
        defaultValue={filters.search}
        onSearch={(value) => {
          reportSearch(value);
          applyFilterChange({ search: value });
        }}
        placeholder="Search by bill number or supplier name…"
        isLoading={query.isFetching}
        aria-label="Search purchase bills"
        className="min-w-56 flex-1"
      />
      <SearchableSelect
        label="Supplier"
        placeholder="All suppliers"
        options={supplierOptions.options}
        value={filters.supplierId ?? undefined}
        onChange={(value) => applyFilterChange({ supplierId: value ?? null })}
      />
      <DateRangeFilter
        label="Date Range"
        value={dateRange}
        onChange={(range) =>
          applyFilterChange({
            fromDate: range?.from ? format(range.from, ISO_DATE_FORMAT) : null,
            toDate: range?.to ? format(range.to, ISO_DATE_FORMAT) : null,
          })
        }
      />
      <StatusFilter
        label="Bill Status"
        options={STATUS_OPTIONS}
        value={filters.status ?? undefined}
        onChange={(value) => applyFilterChange({ status: value ?? null })}
      />
      <StatusFilter
        label="Paid Status"
        options={PAID_STATUS_OPTIONS}
        value={filters.paidStatus ?? undefined}
        onChange={(value) => applyFilterChange({ paidStatus: value ?? null })}
      />
      {hasActiveFilters && (
        <Button variant="ghost" size="sm" onClick={resetFilters}>
          <X aria-hidden />
          Reset
        </Button>
      )}
    </div>
  );

  return (
    <ReportPageTemplate
      title="Purchase Report"
      description="Every posted purchase bill, with server-computed purchase totals."
      exportMenu={
        <ExportMenu
          onExport={(format) =>
            triggerReportDownload("purchase_report", format, toPurchaseReportParams(filters))
          }
        />
      }
      filters={filterBar}
      summary={data ? <PurchaseReportSummaryCards summary={data.summary} /> : undefined}
      isLoading={query.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load the purchase report",
              description: apiError.message,
              onRetry: () => query.refetch(),
            }
          : null
      }
    >
      <DataTable
        table={table}
        isLoading={query.isFetching}
        loadingRowCount={Math.min(filters.pageSize, 10)}
        isEmpty={!query.isLoading && !apiError && rows.length === 0 && !hasActiveFilters}
        emptyState={
          <DataTableEmpty
            title="No purchase bills yet"
            description="Purchase bills you post will appear here."
          />
        }
        isNoResults={!query.isLoading && !apiError && rows.length === 0 && hasActiveFilters}
        noResultsState={<DataTableNoResults onClearFilters={resetFilters} />}
        pagination={
          <DataTablePagination
            pageIndex={filters.page - 1}
            pageSize={filters.pageSize}
            totalCount={data?.pagination.totalRecords ?? 0}
            onPageChange={(pageIndex) => goToPage(pageIndex + 1)}
            onPageSizeChange={setPageSize}
          />
        }
        onRowClick={
          hasPermission("purchase:view")
            ? (row: PurchaseReportRow) => router.push(`/purchase-bills/${row.billId}`)
            : undefined
        }
        stickyHeader
        aria-label="Purchase report"
      />
    </ReportPageTemplate>
  );
}
