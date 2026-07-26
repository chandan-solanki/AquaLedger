"use client";

import {
  Bar,
  BarChart as RechartsBarChart,
  CartesianGrid,
  Legend as RechartsLegend,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";

import { cn } from "@/lib/utils";

import { ChartEmpty } from "./ChartEmpty";
import { ChartError } from "./ChartError";
import { ChartLoading } from "./ChartLoading";
import { ChartTooltip } from "./ChartTooltip";
import { Legend } from "./Legend";
import { getChartColor, type ChartDatum, type ChartSeriesConfig } from "./types";

export interface BarChartProps {
  data: ChartDatum[];
  series: ChartSeriesConfig[];
  xAxisKey: string;
  height?: number;
  /** Stacks every series into a single bar per category instead of grouping them side by side. */
  stacked?: boolean;
  isLoading?: boolean;
  error?: string;
  onRetry?: () => void;
  emptyMessage?: string;
  showLegend?: boolean;
  showGrid?: boolean;
  valueFormatter?: (value: number) => string;
  className?: string;
}

/** A grouped or stacked multi-series bar chart — see `LineChart` for the shared theming/state-prop conventions every chart in this folder follows. */
export function BarChart({
  data,
  series,
  xAxisKey,
  height = 300,
  stacked = false,
  isLoading = false,
  error,
  onRetry,
  emptyMessage,
  showLegend = true,
  showGrid = true,
  valueFormatter,
  className,
}: BarChartProps) {
  if (isLoading) return <ChartLoading height={height} className={className} />;
  if (error) return <ChartError description={error} onRetry={onRetry} height={height} className={className} />;
  if (data.length === 0) return <ChartEmpty description={emptyMessage} height={height} className={className} />;

  return (
    <div className={cn("w-full", className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsBarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />}
          <XAxis
            dataKey={xAxisKey}
            tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: "var(--border)" }}
          />
          <YAxis
            tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            width={48}
            tickFormatter={valueFormatter}
          />
          <RechartsTooltip
            content={
              <ChartTooltip valueFormatter={valueFormatter ? (value) => valueFormatter(Number(value)) : undefined} />
            }
            cursor={{ fill: "var(--muted)" }}
          />
          {showLegend && <RechartsLegend content={<Legend />} />}
          {series.map((s, index) => (
            <Bar
              key={s.dataKey}
              dataKey={s.dataKey}
              name={s.label ?? s.dataKey}
              fill={s.color ?? getChartColor(index)}
              stackId={stacked ? "stack" : undefined}
              radius={stacked ? 0 : [4, 4, 0, 0]}
              maxBarSize={48}
            />
          ))}
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  );
}
