import { Fish, Package, TrendingUp, Wallet } from "lucide-react";

import { SummaryGrid } from "@/components/data-display/summary-grid";
import { MetricCard } from "@/components/data-display/metric-card";
import type { FishSalesSummary } from "@/features/reports/types/fish-sales";
import { formatCurrency } from "@/utils/format-currency";

interface FishSalesSummaryCardsProps {
  summary: FishSalesSummary;
}

/**
 * The Fish Sales Analytics report's Summary KPI row - six figures
 * (TASKS.md Sprint 11 Session 4 Phase B), every one already computed
 * server-side (ReportsService.get_fish_sales) and rendered here as-is.
 */
export function FishSalesSummaryCards({ summary }: FishSalesSummaryCardsProps) {
  return (
    <SummaryGrid columns={3}>
      <MetricCard title="Total Fish Sold" value={summary.totalFishSold} icon={Package} />
      <MetricCard title="Total Revenue" value={formatCurrency(summary.totalRevenue)} icon={Wallet} />
      <MetricCard
        title="Average Selling Price"
        value={formatCurrency(summary.averageSellingPrice)}
        icon={TrendingUp}
      />
      <MetricCard
        title="Best Selling Fish (Quantity)"
        value={summary.bestSellingFishName ?? "—"}
        description={summary.bestSellingFishQuantity ?? undefined}
        icon={Fish}
      />
      <MetricCard
        title="Highest Revenue Fish"
        value={summary.highestRevenueFishName ?? "—"}
        description={
          summary.highestRevenueFishRevenue ? formatCurrency(summary.highestRevenueFishRevenue) : undefined
        }
        icon={Fish}
      />
      <MetricCard title="Total Fish Types Sold" value={String(summary.totalFishTypesSold)} icon={Fish} />
    </SummaryGrid>
  );
}
