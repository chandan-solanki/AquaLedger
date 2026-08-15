import { ArrowDownToLine, ArrowUpFromLine, FileText, TrendingUp, Wallet } from "lucide-react";

import { SummaryGrid } from "@/components/data-display/summary-grid";
import { MetricCard } from "@/components/data-display/metric-card";
import type { PurchaseReportSummary } from "@/features/reports/types/purchase-report";
import { formatCurrency } from "@/utils/format-currency";

interface PurchaseReportSummaryCardsProps {
  summary: PurchaseReportSummary;
}

/**
 * The Purchase Report's Summary KPI row - mirrors
 * `SalesReportSummaryCards` exactly, on the buy side.
 */
export function PurchaseReportSummaryCards({ summary }: PurchaseReportSummaryCardsProps) {
  return (
    <SummaryGrid columns={3}>
      <MetricCard
        title="Total Purchases"
        value={formatCurrency(summary.totalPurchases)}
        icon={ArrowUpFromLine}
      />
      <MetricCard title="Total Paid" value={formatCurrency(summary.totalPaid)} icon={ArrowDownToLine} />
      <MetricCard title="Outstanding" value={formatCurrency(summary.outstanding)} icon={Wallet} />
      <MetricCard title="Bill Count" value={String(summary.billCount)} icon={FileText} />
      <MetricCard
        title="Average Bill"
        value={formatCurrency(summary.averageBill)}
        icon={TrendingUp}
      />
      <MetricCard
        title="Largest Bill"
        value={formatCurrency(summary.largestBill)}
        icon={TrendingUp}
      />
    </SummaryGrid>
  );
}
