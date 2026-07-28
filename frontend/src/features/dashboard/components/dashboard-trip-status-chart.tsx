import { memo, useMemo } from "react";

import { ChartCard, PieChart } from "@/components/charts";
import type { ChartDatum } from "@/components/charts";
import type { DashboardTripStatusPoint } from "@/features/dashboard/types/dashboard";

interface DashboardTripStatusChartProps {
  data: DashboardTripStatusPoint[];
  className?: string;
}

/**
 * TASKS.md Sprint 10 Session 3 "CHART 4 Trip Status Distribution" - a
 * `PieChart` over the backend's four always-present, zero-filled status
 * counts. Zero-count slices are filtered out here purely for legibility (a
 * 0-value pie slice draws nothing meaningful); this is display filtering,
 * not aggregation - every remaining number is still exactly what the
 * backend returned.
 */
function DashboardTripStatusChartImpl({ data, className }: DashboardTripStatusChartProps) {
  const chartData = useMemo<ChartDatum[]>(
    () =>
      data
        .filter((point) => point.count > 0)
        .map((point) => ({ status: point.status, count: point.count })),
    [data]
  );

  return (
    <ChartCard
      title="Trip Status"
      description="Distribution of all trips by status"
      className={className}
    >
      <PieChart
        data={chartData}
        dataKey="count"
        nameKey="status"
        emptyMessage="No trips recorded yet."
      />
    </ChartCard>
  );
}

export const DashboardTripStatusChart = memo(DashboardTripStatusChartImpl);
