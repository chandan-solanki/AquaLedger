import { memo, useMemo } from "react";

import { BarChart, ChartCard } from "@/components/charts";
import type { ChartDatum } from "@/components/charts";
import type { FishSalesPoint } from "@/features/dashboard/types/dashboard";
import { formatCompactCurrency, formatCurrency } from "@/utils/format-currency";

interface DashboardFishSalesChartProps {
  data: FishSalesPoint[];
  className?: string;
}

/**
 * TASKS.md Sprint 10 Session 3 "CHART 3 Fish Sales Distribution" - a
 * horizontal `BarChart` (`layout="vertical"`, Recharts' own naming) over
 * the backend's top-10-by-sales-amount list, already ordered descending
 * server-side; this component only formats for display.
 */
function DashboardFishSalesChartImpl({ data, className }: DashboardFishSalesChartProps) {
  const chartData = useMemo<ChartDatum[]>(
    () =>
      data.map((point) => ({
        fish: point.fishName,
        sales: Number(point.salesAmount),
      })),
    [data]
  );

  return (
    <ChartCard
      title="Fish Sales"
      description="Top 10 fish by sales value"
      className={className}
      height={340}
    >
      <BarChart
        data={chartData}
        series={[{ dataKey: "sales", label: "Sales" }]}
        xAxisKey="fish"
        layout="vertical"
        height={340}
        valueFormatter={(value) => formatCurrency(value)}
        axisValueFormatter={(value) => formatCompactCurrency(value)}
        emptyMessage="No fish sales recorded yet."
      />
    </ChartCard>
  );
}

export const DashboardFishSalesChart = memo(DashboardFishSalesChartImpl);
