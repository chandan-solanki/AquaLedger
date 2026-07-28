"use client";

import {
  CartesianGrid,
  Legend as RechartsLegend,
  Line,
  LineChart as RechartsLineChart,
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

export interface LineChartProps {
  data: ChartDatum[];
  series: ChartSeriesConfig[];
  xAxisKey: string;
  height?: number;
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

/**
 * A multi-series line chart — `ResponsiveContainer`-wrapped, themed off the
 * `--chart-1`…`--chart-5` / `--border` / `--muted-foreground` CSS tokens so
 * it repaints correctly across the light/dark class toggle with no JS theme
 * detection needed, per this session's Recharts requirement.
 */
export function LineChart({
  data,
  series,
  xAxisKey,
  height = 300,
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
}: LineChartProps) {
  if (isLoading) return <ChartLoading height={height} className={className} />;
  if (error) return <ChartError description={error} onRetry={onRetry} height={height} className={className} />;
  if (data.length === 0) return <ChartEmpty description={emptyMessage} height={height} className={className} />;

  return (
    <div className={cn("w-full", className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsLineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
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
          {series.map((s, index) => (
            <Line
              key={s.dataKey}
              type="monotone"
              dataKey={s.dataKey}
              name={s.label ?? s.dataKey}
              stroke={s.color ?? getChartColor(index)}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ))}
        </RechartsLineChart>
      </ResponsiveContainer>
    </div>
  );
}
