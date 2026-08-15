import { ArrowDownToLine, ArrowUpFromLine, TrendingDown, TrendingUp, Wallet } from "lucide-react";

import { SummaryGrid } from "@/components/data-display/summary-grid";
import { MetricCard } from "@/components/data-display/metric-card";
import type { TripProfitabilitySummary } from "@/features/reports/types/trip-profitability";
import { formatCurrency } from "@/utils/format-currency";

interface TripProfitabilitySummaryCardsProps {
  summary: TripProfitabilitySummary;
}

/**
 * The Trip Profitability report's Summary KPI row - seven figures
 * (TASKS.md Sprint 11 Session 4 Phase A), every one already computed
 * server-side (ReportsService.get_trip_profitability) and rendered here
 * as-is.
 */
export function TripProfitabilitySummaryCards({ summary }: TripProfitabilitySummaryCardsProps) {
  return (
    <SummaryGrid columns={4}>
      <MetricCard title="Total Revenue" value={formatCurrency(summary.totalRevenue)} icon={ArrowUpFromLine} />
      <MetricCard title="Total Expenses" value={formatCurrency(summary.totalExpenses)} icon={ArrowDownToLine} />
      <MetricCard title="Total Profit" value={formatCurrency(summary.totalProfit)} icon={Wallet} />
      <MetricCard
        title="Average Profit Per Trip"
        value={formatCurrency(summary.averageProfitPerTrip)}
        icon={TrendingUp}
      />
      <MetricCard
        title="Average Revenue Per Trip"
        value={formatCurrency(summary.averageRevenuePerTrip)}
        icon={TrendingUp}
      />
      <MetricCard
        title="Most Profitable Trip"
        value={summary.mostProfitableTripNumber ?? "—"}
        description={
          summary.mostProfitableTripProfit ? formatCurrency(summary.mostProfitableTripProfit) : undefined
        }
        icon={TrendingUp}
      />
      <MetricCard
        title="Loss Making Trips"
        value={String(summary.lossMakingTrips)}
        icon={TrendingDown}
      />
    </SummaryGrid>
  );
}
