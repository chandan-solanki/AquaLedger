"use client";

import { format, parseISO } from "date-fns";
import { UserSearch, X } from "lucide-react";
import { useCallback, useMemo } from "react";
import type { DateRange } from "react-day-picker";

import {
  DataTable,
  DataTableEmpty,
  DataTableNoResults,
  DataTablePagination,
  useDataTable,
} from "@/components/data-table";
import { DateRangeFilter, StatusFilter } from "@/components/filters";
import { SearchableSelect } from "@/components/form";
import { PageContainer } from "@/components/layout/page-container";
import { ExportMenu } from "@/components/reports";
import { ReportPageTemplate } from "@/components/templates/report-page-template";
import { Button } from "@/components/ui/button";
import { Forbidden } from "@/components/feedback/error-states";
import { CustomerLedgerSummaryCards } from "@/features/reports/components/customer-ledger-summary-cards";
import { getCustomerLedgerColumns } from "@/features/reports/components/customer-ledger-columns";
import { useCustomerLedger } from "@/features/reports/hooks/use-customer-ledger";
import { useCustomerLedgerFilters } from "@/features/reports/hooks/use-customer-ledger-filters";
import { useCustomerOptions } from "@/features/reports/hooks/use-customer-options";
import {
  toCustomerLedgerParams,
  type CustomerLedgerFilters,
} from "@/features/reports/schemas/customer-ledger-filters";
import type { TransactionType } from "@/features/reports/types/customer-ledger";
import { triggerReportDownload } from "@/features/reports/utils/trigger-report-download";
import { normalizeApiError } from "@/utils/api-error";

const TRANSACTION_TYPE_OPTIONS: { value: TransactionType; label: string }[] = [
  { value: "invoice", label: "Invoice" },
  { value: "payment", label: "Payment" },
];

function toDateRange(filters: CustomerLedgerFilters): DateRange | undefined {
  if (!filters.fromDate && !filters.toDate) return undefined;
  return {
    from: filters.fromDate ? parseISO(filters.fromDate) : undefined,
    to: filters.toDate ? parseISO(filters.toDate) : undefined,
  };
}

const ISO_DATE_FORMAT = "yyyy-MM-dd";

/**
 * The Customer Ledger report page (TASKS.md Sprint 11 Session 1) - Filter
 * Bar -> Summary Cards -> Ledger Table, entirely driven by the backend's
 * single GET /reports/customer-ledger response (ReportsService). No total,
 * balance or count is ever computed here - every figure is rendered as-is
 * from `useCustomerLedger()`'s data, only formatted for display, mirroring
 * `InvoiceDetailPage`'s "the backend owns financial calculations" posture.
 *
 * `customer_id` is a required backend param, so nothing is fetched until a
 * customer is picked - `useCustomerLedger` stays `enabled: false` until
 * then, and this page shows a plain prompt state instead of a loading
 * skeleton or an empty table in the meantime.
 */
export function CustomerLedgerPage() {
  const [filters, setFilters] = useCustomerLedgerFilters();
  const customerOptions = useCustomerOptions();
  const query = useCustomerLedger(filters);

  const data = query.data;
  const apiError = query.isError ? normalizeApiError(query.error) : null;
  const hasCustomer = Boolean(filters.customerId);

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<CustomerLedgerFilters, "page">>) => {
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

  const entries = useMemo(() => data?.entries ?? [], [data]);
  const columns = useMemo(() => getCustomerLedgerColumns(), []);
  const table = useDataTable({
    data: entries,
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
      <SearchableSelect
        label="Customer"
        placeholder="Select a customer…"
        options={customerOptions.options}
        value={filters.customerId ?? undefined}
        onChange={(value) => applyFilterChange({ customerId: value ?? null })}
        containerClassName="min-w-64"
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
        label="Transaction Type"
        options={TRANSACTION_TYPE_OPTIONS}
        value={filters.transactionType ?? undefined}
        onChange={(value) => applyFilterChange({ transactionType: value ?? null })}
      />
      <Button variant="ghost" size="sm" onClick={resetFilters}>
        <X aria-hidden />
        Reset
      </Button>
    </div>
  );

  return (
    <ReportPageTemplate
      title="Customer Ledger"
      description="A chronological, running-balance accounting ledger for one customer."
      exportMenu={
        <ExportMenu
          disabled={!hasCustomer}
          onExport={(format) =>
            triggerReportDownload("customer_ledger", format, toCustomerLedgerParams(filters) ?? {})
          }
        />
      }
      filters={filterBar}
      summary={data ? <CustomerLedgerSummaryCards summary={data.summary} /> : undefined}
      isLoading={hasCustomer && query.isLoading}
      error={
        apiError && hasCustomer
          ? {
              title: "Failed to load the customer ledger",
              description: apiError.message,
              onRetry: () => query.refetch(),
            }
          : null
      }
      isEmpty={!hasCustomer}
      emptyState={
        <div className="flex flex-col items-center gap-2 py-16 text-center text-muted-foreground">
          <UserSearch className="size-9" aria-hidden />
          <p className="text-sm font-medium text-foreground">Select a customer to get started</p>
          <p className="text-sm">
            Choose a customer above to view their invoices, payments and running balance.
          </p>
        </div>
      }
    >
      <DataTable
        table={table}
        isLoading={query.isFetching}
        loadingRowCount={Math.min(filters.pageSize, 10)}
        isEmpty={!query.isLoading && !apiError && entries.length === 0}
        emptyState={
          <DataTableEmpty
            title="No transactions in this range"
            description="Try widening the date range or clearing the transaction type filter."
          />
        }
        isNoResults={
          !query.isLoading &&
          !apiError &&
          entries.length === 0 &&
          Boolean(filters.fromDate || filters.toDate || filters.transactionType)
        }
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
        stickyHeader
        aria-label="Customer ledger entries"
      />
    </ReportPageTemplate>
  );
}
