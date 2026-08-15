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
import { SalesReportSummaryCards } from "@/features/reports/components/sales-report-summary-cards";
import { getSalesReportColumns } from "@/features/reports/components/sales-report-columns";
import { PAID_STATUS_OPTIONS } from "@/features/reports/constants/paid-status";
import { useCustomerOptions } from "@/features/reports/hooks/use-customer-options";
import { useSalesReport } from "@/features/reports/hooks/use-sales-report";
import { useSalesReportFilters } from "@/features/reports/hooks/use-sales-report-filters";
import {
  toSalesReportParams,
  type SalesReportFilters,
} from "@/features/reports/schemas/sales-report-filters";
import type { SalesReportInvoiceStatus, SalesReportRow } from "@/features/reports/types/sales-report";
import { triggerReportDownload } from "@/features/reports/utils/trigger-report-download";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { normalizeApiError } from "@/utils/api-error";

const STATUS_OPTIONS: { value: SalesReportInvoiceStatus; label: string }[] = [
  { value: "issued", label: "Issued" },
  { value: "partially_paid", label: "Partially Paid" },
  { value: "paid", label: "Paid" },
  { value: "cancelled", label: "Cancelled" },
];

function toDateRange(filters: SalesReportFilters): DateRange | undefined {
  if (!filters.fromDate && !filters.toDate) return undefined;
  return {
    from: filters.fromDate ? parseISO(filters.fromDate) : undefined,
    to: filters.toDate ? parseISO(filters.toDate) : undefined,
  };
}

const ISO_DATE_FORMAT = "yyyy-MM-dd";

/**
 * The Sales Report page (TASKS.md Sprint 11 Session 3) - Filter Bar ->
 * Summary Cards -> Report Table, entirely driven by the backend's single
 * GET /reports/sales response. Unlike the Ledger pages, there is no "pick
 * an entity first" gate - `customer_id` is an optional narrowing filter,
 * so the report loads with every issued invoice by default (mirrors
 * `InvoiceListPage`'s own posture). Clicking a row navigates to the
 * existing Invoice Detail page, gated on `invoice:view` (a user with
 * `reports:view` alone can see the report but not necessarily drill into
 * an invoice).
 */
export function SalesReportPage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = useSalesReportFilters();
  const [searchKey, reportSearch] = useExternalValueKey(filters.search);
  const customerOptions = useCustomerOptions();
  const query = useSalesReport(filters);

  const data = query.data;
  const apiError = query.isError ? normalizeApiError(query.error) : null;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<SalesReportFilters, "page">>) => {
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
      filters.customerId ||
      filters.status ||
      filters.paidStatus ||
      filters.fromDate ||
      filters.toDate
  );

  const rows = useMemo(() => data?.rows ?? [], [data]);
  const columns = useMemo(() => getSalesReportColumns(), []);
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
        placeholder="Search by invoice number or customer name…"
        isLoading={query.isFetching}
        aria-label="Search invoices"
        className="min-w-56 flex-1"
      />
      <SearchableSelect
        label="Customer"
        placeholder="All customers"
        options={customerOptions.options}
        value={filters.customerId ?? undefined}
        onChange={(value) => applyFilterChange({ customerId: value ?? null })}
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
        label="Invoice Status"
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
      title="Sales Report"
      description="Every issued invoice, with server-computed sales totals."
      exportMenu={
        <ExportMenu
          onExport={(format) => triggerReportDownload("sales_report", format, toSalesReportParams(filters))}
        />
      }
      filters={filterBar}
      summary={data ? <SalesReportSummaryCards summary={data.summary} /> : undefined}
      isLoading={query.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load the sales report",
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
            title="No invoices yet"
            description="Invoices you issue will appear here."
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
          hasPermission("invoice:view")
            ? (row: SalesReportRow) => router.push(`/invoices/${row.invoiceId}`)
            : undefined
        }
        stickyHeader
        aria-label="Sales report"
      />
    </ReportPageTemplate>
  );
}
