"use client";

import { useRouter } from "next/navigation";
import { X } from "lucide-react";
import { useCallback, useMemo } from "react";

import {
  DataTable,
  DataTableEmpty,
  DataTableNoResults,
  DataTablePagination,
  useDataTable,
} from "@/components/data-table";
import { BooleanFilter, SearchBar, StatusFilter } from "@/components/filters";
import { PageContainer } from "@/components/layout/page-container";
import { ExportMenu } from "@/components/reports";
import { ReportPageTemplate } from "@/components/templates/report-page-template";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Forbidden } from "@/components/feedback/error-states";
import { getAgingReportColumns } from "@/features/reports/components/aging-report-columns";
import { AgingReportSummaryCards } from "@/features/reports/components/aging-report-summary-cards";
import { RISK_LEVEL_OPTIONS } from "@/features/reports/constants/risk-level";
import { useAgingReport } from "@/features/reports/hooks/use-aging-report";
import { useAgingReportFilters } from "@/features/reports/hooks/use-aging-report-filters";
import {
  toAgingReportParams,
  type AgingReportFilters,
} from "@/features/reports/schemas/aging-report-filters";
import type { AgingReportRow } from "@/features/reports/types/aging-report";
import { triggerReportDownload } from "@/features/reports/utils/trigger-report-download";
import { useExternalValueKey } from "@/hooks/use-external-value-key";
import { normalizeApiError } from "@/utils/api-error";

/**
 * The Aging Report page (TASKS.md Sprint 11 Session 3 Phase B) - mirrors
 * `OutstandingReportPage`'s structure with a smaller filter set (no
 * "Overdue Only", no Date Range - aging is always "as of today"). Clicking
 * a row drills into that entity's Customer/Supplier Ledger, same as
 * Outstanding.
 */
export function AgingReportPage() {
  const router = useRouter();
  const [filters, setFilters] = useAgingReportFilters();
  const [searchKey, reportSearch] = useExternalValueKey(filters.search);
  const query = useAgingReport(filters);

  const data = query.data;
  const apiError = query.isError ? normalizeApiError(query.error) : null;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<AgingReportFilters, "page">>) => {
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

  const hasActiveFilters = Boolean(
    filters.search.trim() || filters.outstandingOnly || filters.riskLevel
  );

  const rows = useMemo(() => data?.rows ?? [], [data]);
  const columns = useMemo(() => getAgingReportColumns(filters.entityType), [filters.entityType]);
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

  const tabs = (
    <Tabs
      value={filters.entityType}
      onValueChange={(value) => applyFilterChange({ entityType: value as "customer" | "supplier" })}
    >
      <TabsList>
        <TabsTrigger value="customer">Customer Aging</TabsTrigger>
        <TabsTrigger value="supplier">Supplier Aging</TabsTrigger>
      </TabsList>
    </Tabs>
  );

  const filterBar = (
    <div className="flex flex-col gap-3">
      {tabs}
      <div className="flex flex-wrap items-end gap-3">
        <SearchBar
          key={searchKey}
          defaultValue={filters.search}
          onSearch={(value) => {
            reportSearch(value);
            applyFilterChange({ search: value });
          }}
          placeholder="Search by name or code…"
          isLoading={query.isFetching}
          aria-label="Search entities"
          className="min-w-56 flex-1"
        />
        <StatusFilter
          label="Risk Level"
          options={RISK_LEVEL_OPTIONS}
          value={filters.riskLevel ?? undefined}
          onChange={(value) => applyFilterChange({ riskLevel: value ?? null })}
        />
        <BooleanFilter
          label="Outstanding Only"
          checked={filters.outstandingOnly}
          onChange={(checked) => applyFilterChange({ outstandingOnly: checked })}
        />
        {hasActiveFilters && (
          <Button variant="ghost" size="sm" onClick={resetFilters}>
            <X aria-hidden />
            Reset
          </Button>
        )}
      </div>
    </div>
  );

  return (
    <ReportPageTemplate
      title="Aging Report"
      description="Receivables and payables bucketed by how overdue they are, by due date."
      exportMenu={
        <ExportMenu
          onExport={(format) => triggerReportDownload("aging_report", format, toAgingReportParams(filters))}
        />
      }
      filters={filterBar}
      summary={data ? <AgingReportSummaryCards summary={data.summary} /> : undefined}
      isLoading={query.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load the aging report",
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
            title={filters.entityType === "customer" ? "No customers yet" : "No suppliers yet"}
            description="Entities with invoice/purchase-bill history will appear here."
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
        onRowClick={(row: AgingReportRow) =>
          router.push(
            filters.entityType === "customer"
              ? `/reports/customer-ledger?customerId=${row.entityId}`
              : `/reports/supplier-ledger?supplierId=${row.entityId}`
          )
        }
        stickyHeader
        aria-label="Aging report"
      />
    </ReportPageTemplate>
  );
}
