"use client";

import { format, parseISO } from "date-fns";
import { Truck, X } from "lucide-react";
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
import { SupplierLedgerSummaryCards } from "@/features/reports/components/supplier-ledger-summary-cards";
import { getSupplierLedgerColumns } from "@/features/reports/components/supplier-ledger-columns";
import { useSupplierLedger } from "@/features/reports/hooks/use-supplier-ledger";
import { useSupplierLedgerFilters } from "@/features/reports/hooks/use-supplier-ledger-filters";
import { useSupplierOptions } from "@/features/reports/hooks/use-supplier-options";
import {
  toSupplierLedgerParams,
  type SupplierLedgerFilters,
} from "@/features/reports/schemas/supplier-ledger-filters";
import type { SupplierTransactionType } from "@/features/reports/types/supplier-ledger";
import { triggerReportDownload } from "@/features/reports/utils/trigger-report-download";
import { normalizeApiError } from "@/utils/api-error";

const TRANSACTION_TYPE_OPTIONS: { value: SupplierTransactionType; label: string }[] = [
  { value: "purchase_bill", label: "Purchase Bill" },
  { value: "supplier_payment", label: "Supplier Payment" },
];

function toDateRange(filters: SupplierLedgerFilters): DateRange | undefined {
  if (!filters.fromDate && !filters.toDate) return undefined;
  return {
    from: filters.fromDate ? parseISO(filters.fromDate) : undefined,
    to: filters.toDate ? parseISO(filters.toDate) : undefined,
  };
}

const ISO_DATE_FORMAT = "yyyy-MM-dd";

/**
 * The Supplier Ledger report page (TASKS.md Sprint 11 Session 2) - Filter
 * Bar -> Summary Cards -> Ledger Table, entirely driven by the backend's
 * single GET /reports/supplier-ledger response (ReportsService). Mirrors
 * `CustomerLedgerPage` exactly, on the buy side: no total, balance or count
 * is ever computed here - every figure is rendered as-is from
 * `useSupplierLedger()`'s data, only formatted for display.
 *
 * `supplier_id` is a required backend param, so nothing is fetched until a
 * supplier is picked - `useSupplierLedger` stays `enabled: false` until
 * then, and this page shows a plain prompt state instead of a loading
 * skeleton or an empty table in the meantime.
 */
export function SupplierLedgerPage() {
  const [filters, setFilters] = useSupplierLedgerFilters();
  const supplierOptions = useSupplierOptions();
  const query = useSupplierLedger(filters);

  const data = query.data;
  const apiError = query.isError ? normalizeApiError(query.error) : null;
  const hasSupplier = Boolean(filters.supplierId);

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<SupplierLedgerFilters, "page">>) => {
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
  const columns = useMemo(() => getSupplierLedgerColumns(), []);
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
        label="Supplier"
        placeholder="Select a supplier…"
        options={supplierOptions.options}
        value={filters.supplierId ?? undefined}
        onChange={(value) => applyFilterChange({ supplierId: value ?? null })}
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
      title="Supplier Ledger"
      description="A chronological, running-balance accounting ledger for one supplier."
      exportMenu={
        <ExportMenu
          disabled={!hasSupplier}
          onExport={(format) =>
            triggerReportDownload("supplier_ledger", format, toSupplierLedgerParams(filters) ?? {})
          }
        />
      }
      filters={filterBar}
      summary={data ? <SupplierLedgerSummaryCards summary={data.summary} /> : undefined}
      isLoading={hasSupplier && query.isLoading}
      error={
        apiError && hasSupplier
          ? {
              title: "Failed to load the supplier ledger",
              description: apiError.message,
              onRetry: () => query.refetch(),
            }
          : null
      }
      isEmpty={!hasSupplier}
      emptyState={
        <div className="flex flex-col items-center gap-2 py-16 text-center text-muted-foreground">
          <Truck className="size-9" aria-hidden />
          <p className="text-sm font-medium text-foreground">Select a supplier to get started</p>
          <p className="text-sm">
            Choose a supplier above to view their purchase bills, payments and running balance.
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
        aria-label="Supplier ledger entries"
      />
    </ReportPageTemplate>
  );
}
