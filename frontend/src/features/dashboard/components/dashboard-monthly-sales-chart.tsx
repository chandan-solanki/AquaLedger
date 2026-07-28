import { memo, useMemo } from "react";

import { ChartCard, LineChart } from "@/components/charts";
import type { ChartDatum } from "@/components/charts";
import type { MonthlySalesPoint } from "@/features/dashboard/types/dashboard";
import { formatCompactCurrency, formatCurrency } from "@/utils/format-currency";
import { formatMonth } from "@/utils/format-date";

interface DashboardMonthlySalesChartProps {
  data: MonthlySalesPoint[];
  className?: string;
}

/**
 * TASKS.md Sprint 10 Session 3 "CHART 1 Monthly Sales" - a `LineChart` over
 * the backend's already-aggregated, already-zero-filled trailing-12-month
 * series. The only work done here is reshaping already-final numbers into
 * `ChartDatum` (a month label plus a plain JS number Recharts can plot) -
 * never summing or grouping raw invoice rows.
 */
function DashboardMonthlySalesChartImpl({ data, className }: DashboardMonthlySalesChartProps) {
  const chartData = useMemo<ChartDatum[]>(
    () =>
      data.map((point) => ({
        month: formatMonth(point.month),
        sales: Number(point.salesAmount),
      })),
    [data]
  );

  return (
    <ChartCard
      title="Monthly Sales"
      description="Invoice revenue over the last 12 months"
      className={className}
    >
      <LineChart
        data={chartData}
        series={[{ dataKey: "sales", label: "Sales" }]}
        xAxisKey="month"
        valueFormatter={(value) => formatCurrency(value)}
        axisValueFormatter={(value) => formatCompactCurrency(value)}
        emptyMessage="No sales recorded in the last 12 months."
      />
    </ChartCard>
  );
}

export const DashboardMonthlySalesChart = memo(DashboardMonthlySalesChartImpl);
