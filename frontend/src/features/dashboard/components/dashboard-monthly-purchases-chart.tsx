import { memo, useMemo } from "react";

import { AreaChart, ChartCard } from "@/components/charts";
import type { ChartDatum } from "@/components/charts";
import type { MonthlyPurchasesPoint } from "@/features/dashboard/types/dashboard";
import { formatCompactCurrency, formatCurrency } from "@/utils/format-currency";
import { formatMonth } from "@/utils/format-date";

interface DashboardMonthlyPurchasesChartProps {
  data: MonthlyPurchasesPoint[];
  className?: string;
}

/**
 * TASKS.md Sprint 10 Session 3 "CHART 2 Monthly Purchases" - mirrors
 * DashboardMonthlySalesChart on the buy side, rendered as an `AreaChart`
 * per the session's Recharts assignment.
 */
function DashboardMonthlyPurchasesChartImpl({
  data,
  className,
}: DashboardMonthlyPurchasesChartProps) {
  const chartData = useMemo<ChartDatum[]>(
    () =>
      data.map((point) => ({
        month: formatMonth(point.month),
        purchases: Number(point.purchaseAmount),
      })),
    [data]
  );

  return (
    <ChartCard
      title="Monthly Purchases"
      description="Purchase bill spend over the last 12 months"
      className={className}
    >
      <AreaChart
        data={chartData}
        series={[{ dataKey: "purchases", label: "Purchases" }]}
        xAxisKey="month"
        valueFormatter={(value) => formatCurrency(value)}
        axisValueFormatter={(value) => formatCompactCurrency(value)}
        emptyMessage="No purchases recorded in the last 12 months."
      />
    </ChartCard>
  );
}

export const DashboardMonthlyPurchasesChart = memo(DashboardMonthlyPurchasesChartImpl);
