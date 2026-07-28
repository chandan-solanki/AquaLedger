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
  /**
   * "horizontal" (default) draws upright bars along a categorical X axis.
   * "vertical" draws horizontal bars along a categorical Y axis instead -
   * Recharts' own (counterintuitive) naming for the two orientations,
   * kept as-is here rather than inventing a clearer name that would then
   * disagree with the `layout` prop Recharts actually reads.
   */
  layout?: "horizontal" | "vertical";
  isLoading?: boolean;
  error?: string;
  onRetry?: () => void;
  emptyMessage?: string;
  showLegend?: boolean;
  showGrid?: boolean;
  valueFormatter?: (value: number) => string;
  /** Formats the numeric axis' own tick labels specifically - defaults to `valueFormatter` when omitted. Pass a shorter form (e.g. a compact currency formatter) when `valueFormatter` is too wide to fit; the tooltip keeps using `valueFormatter` either way. */
  axisValueFormatter?: (value: number) => string;
  /** Width reserved for the category axis when `layout="vertical"` - wider category labels (e.g. names) need more room than the default. */
  categoryAxisWidth?: number;
  /** Width reserved for the numeric Y axis when `layout="horizontal"` (the default) - widen it if tick labels are still clipped after supplying a shorter `axisValueFormatter`. */
  valueAxisWidth?: number;
  className?: string;
}

/** A grouped or stacked multi-series bar chart — see `LineChart` for the shared theming/state-prop conventions every chart in this folder follows. */
export function BarChart({
  data,
  series,
  xAxisKey,
  height = 300,
  stacked = false,
  layout = "horizontal",
  isLoading = false,
  error,
  onRetry,
  emptyMessage,
  showLegend = true,
  showGrid = true,
  valueFormatter,
  axisValueFormatter,
  categoryAxisWidth = 96,
  valueAxisWidth = 64,
  className,
}: BarChartProps) {
  if (isLoading) return <ChartLoading height={height} className={className} />;
  if (error) return <ChartError description={error} onRetry={onRetry} height={height} className={className} />;
  if (data.length === 0) return <ChartEmpty description={emptyMessage} height={height} className={className} />;

  const isHorizontalBars = layout === "vertical";
  const categoryAxisTick = { fill: "var(--muted-foreground)", fontSize: 12 };

  return (
    <div className={cn("w-full", className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsBarChart
          data={data}
          layout={layout}
          margin={{ top: 8, right: 8, left: isHorizontalBars ? 8 : 0, bottom: 0 }}
        >
          {showGrid && (
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border)"
              horizontal={!isHorizontalBars}
              vertical={isHorizontalBars}
            />
          )}
          {isHorizontalBars ? (
            <>
              <XAxis
                type="number"
                tick={categoryAxisTick}
                tickLine={false}
                axisLine={false}
                tickFormatter={axisValueFormatter ?? valueFormatter}
              />
              <YAxis
                type="category"
                dataKey={xAxisKey}
                tick={categoryAxisTick}
                tickLine={false}
                axisLine={{ stroke: "var(--border)" }}
                width={categoryAxisWidth}
              />
            </>
          ) : (
            <>
              <XAxis
                dataKey={xAxisKey}
                tick={categoryAxisTick}
                tickLine={false}
                axisLine={{ stroke: "var(--border)" }}
              />
              <YAxis
                tick={categoryAxisTick}
                tickLine={false}
                axisLine={false}
                width={valueAxisWidth}
                tickFormatter={axisValueFormatter ?? valueFormatter}
              />
            </>
          )}
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
              radius={stacked ? 0 : isHorizontalBars ? [0, 4, 4, 0] : [4, 4, 0, 0]}
              maxBarSize={48}
            />
          ))}
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  );
}
