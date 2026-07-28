"use client";

import { useId } from "react";
import {
  Area,
  AreaChart as RechartsAreaChart,
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

export interface AreaChartProps {
  data: ChartDatum[];
  series: ChartSeriesConfig[];
  xAxisKey: string;
  height?: number;
  stacked?: boolean;
  isLoading?: boolean;
  error?: string;
  onRetry?: () => void;
  emptyMessage?: string;
  showLegend?: boolean;
  showGrid?: boolean;
  valueFormatter?: (value: number) => string;
  /** Formats the Y axis' own tick labels specifically - defaults to `valueFormatter` when omitted. Pass a shorter form (e.g. a compact currency formatter) when `valueFormatter` is too wide to fit the axis; the tooltip keeps using `valueFormatter` either way. */
  axisValueFormatter?: (value: number) => string;
  /** Width reserved for the Y axis - widen it if tick labels are still clipped after supplying a shorter `axisValueFormatter`. */
  yAxisWidth?: number;
  className?: string;
}

/** A multi-series area chart with a gradient fill fading to transparent — see `LineChart` for the shared theming/state-prop conventions every chart in this folder follows. */
export function AreaChart({
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
  axisValueFormatter,
  yAxisWidth = 64,
  className,
}: AreaChartProps) {
  // Scopes each series' gradient `id` to this chart instance — plain
  // `dataKey`-based ids would collide with another `AreaChart` on the same
  // page sharing a series name (e.g. two charts both plotting "revenue").
  const chartId = useId();

  if (isLoading) return <ChartLoading height={height} className={className} />;
  if (error) return <ChartError description={error} onRetry={onRetry} height={height} className={className} />;
  if (data.length === 0) return <ChartEmpty description={emptyMessage} height={height} className={className} />;

  return (
    <div className={cn("w-full", className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsAreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            {series.map((s, index) => {
              const color = s.color ?? getChartColor(index);
              return (
                <linearGradient key={s.dataKey} id={`${chartId}-${s.dataKey}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={color} stopOpacity={0.35} />
                  <stop offset="95%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              );
            })}
          </defs>
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
            width={yAxisWidth}
            tickFormatter={axisValueFormatter ?? valueFormatter}
          />
          <RechartsTooltip
            content={
              <ChartTooltip valueFormatter={valueFormatter ? (value) => valueFormatter(Number(value)) : undefined} />
            }
            cursor={{ stroke: "var(--border)" }}
          />
          {showLegend && <RechartsLegend content={<Legend />} />}
          {series.map((s, index) => {
            const color = s.color ?? getChartColor(index);
            return (
              <Area
                key={s.dataKey}
                type="monotone"
                dataKey={s.dataKey}
                name={s.label ?? s.dataKey}
                stroke={color}
                fill={`url(#${chartId}-${s.dataKey})`}
                strokeWidth={2}
                stackId={stacked ? "stack" : undefined}
              />
            );
          })}
        </RechartsAreaChart>
      </ResponsiveContainer>
    </div>
  );
}
