import { Anchor, ArrowDownToLine, ArrowUpFromLine, Ship, TrendingUp, Wallet } from "lucide-react";

import { SummaryGrid } from "@/components/data-display/summary-grid";
import { MetricCard } from "@/components/data-display/metric-card";
import type { BoatProfitabilitySummary } from "@/features/reports/types/boat-profitability";
import { formatCurrency } from "@/utils/format-currency";

interface BoatProfitabilitySummaryCardsProps {
  summary: BoatProfitabilitySummary;
}

/**
 * The Boat Profitability report's Summary KPI row - eight figures
 * (TASKS.md Sprint 11 Session 4 Phase A), every one already computed
 * server-side (ReportsService.get_boat_profitability) and rendered here
 * as-is.
 */
export function BoatProfitabilitySummaryCards({ summary }: BoatProfitabilitySummaryCardsProps) {
  return (
    <SummaryGrid columns={4}>
      <MetricCard title="Fleet Revenue" value={formatCurrency(summary.fleetRevenue)} icon={ArrowUpFromLine} />
      <MetricCard title="Fleet Expenses" value={formatCurrency(summary.fleetExpenses)} icon={ArrowDownToLine} />
      <MetricCard title="Fleet Profit" value={formatCurrency(summary.fleetProfit)} icon={Wallet} />
      <MetricCard title="Fleet Margin %" value={`${summary.fleetMarginPercent}%`} icon={TrendingUp} />
      <MetricCard title="Total Boats" value={String(summary.totalBoats)} icon={Ship} />
      <MetricCard title="Active Boats" value={String(summary.activeBoats)} icon={Anchor} />
      <MetricCard
        title="Average Profit Per Boat"
        value={formatCurrency(summary.averageProfitPerBoat)}
        icon={TrendingUp}
      />
      <MetricCard
        title="Most Profitable Boat"
        value={summary.mostProfitableBoatName ?? "—"}
        description={
          summary.mostProfitableBoatProfit ? formatCurrency(summary.mostProfitableBoatProfit) : undefined
        }
        icon={TrendingUp}
      />
    </SummaryGrid>
  );
}
