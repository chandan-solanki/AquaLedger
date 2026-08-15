"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Fish as FishIcon, Package, TrendingUp, Users, Wallet } from "lucide-react";

import { MetricCard } from "@/components/data-display/metric-card";
import { SummaryGrid } from "@/components/data-display/summary-grid";
import { InfoCard } from "@/components/data-display/info-card";
import {
  DataTable,
  DataTableEmpty,
  DataTablePagination,
  useDataTable,
} from "@/components/data-table";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { CardSkeleton } from "@/components/feedback/skeletons/card-skeleton";
import { SectionHeader } from "@/components/layout/section-header";
import { getFishSalesHistoryColumns } from "@/features/fish/components/fish-sales-history-columns";
import { useFishLifetimeSales, useFishSalesHistory } from "@/features/reports";
import type { FishSalesHistoryRow } from "@/features/reports";
import { formatCurrency } from "@/utils/format-currency";
import { formatDate } from "@/utils/format-date";
import { normalizeApiError } from "@/utils/api-error";

export interface FishSalesAnalyticsTabProps {
  fishId: string;
}

const SALES_HISTORY_PAGE_SIZE = 20;

/**
 * The Fish Detail page's Sales Analytics tab (TASKS.md Sprint 11 Session 4
 * Phase B "SALES ANALYTICS TAB") - a Lifetime Summary (this one fish's own
 * row from GET /reports/fish-sales, narrowed to `fish_id`) plus its full
 * Sales History (every individual sale, from GET /reports/fish-sales-history).
 * Both reuse the Reports feature's own public hooks/types - no duplicated
 * calculation, mirroring the Boat Detail page's own Profitability tab.
 */
export function FishSalesAnalyticsTab({ fishId }: FishSalesAnalyticsTabProps) {
  const router = useRouter();
  const [page, setPage] = useState(1);

  const lifetimeQuery = useFishLifetimeSales(fishId);
  const historyQuery = useFishSalesHistory(fishId, page, SALES_HISTORY_PAGE_SIZE);

  const fishRow = lifetimeQuery.data?.rows[0];
  const lifetimeError = lifetimeQuery.isError ? normalizeApiError(lifetimeQuery.error) : null;

  const rows = useMemo(() => historyQuery.data?.rows ?? [], [historyQuery.data]);
  const historyError = historyQuery.isError ? normalizeApiError(historyQuery.error) : null;
  const columns = useMemo(() => getFishSalesHistoryColumns(), []);
  const table = useDataTable({ data: rows, columns });

  return (
    <div className="space-y-6">
      <SectionHeader title="Lifetime Summary" />
      {lifetimeQuery.isLoading ? (
        <CardSkeleton lines={4} />
      ) : lifetimeError ? (
        <ErrorState
          title="Failed to load sales summary"
          description={lifetimeError.message}
          onRetry={() => lifetimeQuery.refetch()}
        />
      ) : fishRow ? (
        <SummaryGrid columns={4}>
          <MetricCard title="Lifetime Revenue" value={formatCurrency(fishRow.revenue)} icon={Wallet} />
          <MetricCard title="Lifetime Quantity Sold" value={fishRow.quantitySold} icon={Package} />
          <MetricCard
            title="Average Selling Price"
            value={formatCurrency(fishRow.averageSellingPrice)}
            icon={TrendingUp}
          />
          <MetricCard title="Invoice Count" value={String(fishRow.invoiceCount)} icon={FishIcon} />
          <MetricCard title="Trip Count" value={String(fishRow.tripCount)} icon={FishIcon} />
          <MetricCard title="Customer Count" value={String(fishRow.customerCount)} icon={Users} />
          <MetricCard
            title="Last Sold Date"
            value={fishRow.lastSoldDate ? formatDate(fishRow.lastSoldDate) : "—"}
            icon={FishIcon}
          />
        </SummaryGrid>
      ) : (
        <EmptyState
          title="No sales yet"
          description="This fish's sales summary will appear here once it has at least one sale."
        />
      )}

      <SectionHeader title="Sales History" />
      <InfoCard>
        <DataTable
          table={table}
          isLoading={historyQuery.isLoading}
          error={
            historyError
              ? {
                  title: "Failed to load sales history",
                  description: historyError.message,
                  onRetry: () => historyQuery.refetch(),
                }
              : null
          }
          isEmpty={!historyQuery.isLoading && !historyError && rows.length === 0}
          emptyState={
            <DataTableEmpty title="No sales yet" description="Sales of this fish will appear here." />
          }
          pagination={
            <DataTablePagination
              pageIndex={page - 1}
              pageSize={SALES_HISTORY_PAGE_SIZE}
              totalCount={historyQuery.data?.pagination.totalRecords ?? 0}
              onPageChange={(pageIndex) => setPage(pageIndex + 1)}
            />
          }
          onRowClick={(row: FishSalesHistoryRow) => router.push(`/invoices/${row.invoiceId}`)}
          stickyActionColumn
          aria-label="Sales history"
        />
      </InfoCard>
    </div>
  );
}
