import { Wallet } from "lucide-react";

import { SummaryGrid } from "@/components/data-display/summary-grid";
import { MetricCard } from "@/components/data-display/metric-card";
import type { AgingReportSummary } from "@/features/reports/types/aging-report";
import { formatCurrency } from "@/utils/format-currency";

interface AgingReportSummaryCardsProps {
  summary: AgingReportSummary;
}

/**
 * The Aging Report's Summary KPI row - six bucket totals (TASKS.md Sprint
 * 11 Session 3 Phase B), scoped to the active tab/filters - unlike
 * Outstanding's summary, these change with `entityType` and every row
 * filter (see AgingReportSummary's own backend docstring).
 */
export function AgingReportSummaryCards({ summary }: AgingReportSummaryCardsProps) {
  return (
    <SummaryGrid columns={3}>
      <MetricCard title="Current Total" value={formatCurrency(summary.currentTotal)} icon={Wallet} />
      <MetricCard
        title="1-30 Total"
        value={formatCurrency(summary.days1To30Total)}
        icon={Wallet}
      />
      <MetricCard
        title="31-60 Total"
        value={formatCurrency(summary.days31To60Total)}
        icon={Wallet}
      />
      <MetricCard
        title="61-90 Total"
        value={formatCurrency(summary.days61To90Total)}
        icon={Wallet}
      />
      <MetricCard
        title="90+ Total"
        value={formatCurrency(summary.days90PlusTotal)}
        icon={Wallet}
      />
      <MetricCard title="Grand Total" value={formatCurrency(summary.grandTotal)} icon={Wallet} />
    </SummaryGrid>
  );
}
