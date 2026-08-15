import { ArrowDownToLine, ArrowUpFromLine, FileText, TrendingUp, Wallet } from "lucide-react";

import { SummaryGrid } from "@/components/data-display/summary-grid";
import { MetricCard } from "@/components/data-display/metric-card";
import type { SalesReportSummary } from "@/features/reports/types/sales-report";
import { formatCurrency } from "@/utils/format-currency";

interface SalesReportSummaryCardsProps {
  summary: SalesReportSummary;
}

/**
 * The Sales Report's Summary KPI row - six figures (TASKS.md Sprint 11
 * Session 3), every one already computed server-side
 * (ReportsService.get_sales_report) and rendered here as-is.
 */
export function SalesReportSummaryCards({ summary }: SalesReportSummaryCardsProps) {
  return (
    <SummaryGrid columns={3}>
      <MetricCard title="Total Sales" value={formatCurrency(summary.totalSales)} icon={ArrowUpFromLine} />
      <MetricCard title="Total Paid" value={formatCurrency(summary.totalPaid)} icon={ArrowDownToLine} />
      <MetricCard title="Outstanding" value={formatCurrency(summary.outstanding)} icon={Wallet} />
      <MetricCard title="Invoice Count" value={String(summary.invoiceCount)} icon={FileText} />
      <MetricCard
        title="Average Invoice"
        value={formatCurrency(summary.averageInvoice)}
        icon={TrendingUp}
      />
      <MetricCard
        title="Largest Invoice"
        value={formatCurrency(summary.largestInvoice)}
        icon={TrendingUp}
      />
    </SummaryGrid>
  );
}
