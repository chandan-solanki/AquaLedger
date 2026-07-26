"use client";

import type { ReactNode } from "react";
import { Cell, Legend as RechartsLegend, Pie, PieChart as RechartsPieChart, ResponsiveContainer, Tooltip as RechartsTooltip } from "recharts";

import { cn } from "@/lib/utils";

import { ChartEmpty } from "./ChartEmpty";
import { ChartError } from "./ChartError";
import { ChartLoading } from "./ChartLoading";
import { ChartTooltip } from "./ChartTooltip";
import { Legend } from "./Legend";
import { getChartColor, type ChartDatum } from "./types";

export interface PieChartProps {
  data: ChartDatum[];
  dataKey: string;
  nameKey: string;
  height?: number;
  innerRadius?: number | string;
  outerRadius?: number | string;
  isLoading?: boolean;
  error?: string;
  onRetry?: () => void;
  emptyMessage?: string;
  showLegend?: boolean;
  valueFormatter?: (value: unknown) => ReactNode;
  className?: string;
}

/**
 * A single-series pie chart — each slice colored from the `CHART_COLORS`
 * palette by position. `DonutChart` is this component with `innerRadius`
 * pre-configured, not a separate implementation.
 */
export function PieChart({
  data,
  dataKey,
  nameKey,
  height = 300,
  innerRadius = 0,
  outerRadius = "80%",
  isLoading = false,
  error,
  onRetry,
  emptyMessage,
  showLegend = true,
  valueFormatter,
  className,
}: PieChartProps) {
  if (isLoading) return <ChartLoading height={height} className={className} />;
  if (error) return <ChartError description={error} onRetry={onRetry} height={height} className={className} />;
  if (data.length === 0) return <ChartEmpty description={emptyMessage} height={height} className={className} />;

  return (
    <div className={cn("w-full", className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsPieChart>
          <RechartsTooltip
            content={<ChartTooltip valueFormatter={valueFormatter ? (value) => valueFormatter(value) : undefined} />}
          />
          {showLegend && <RechartsLegend content={<Legend />} />}
          <Pie
            data={data}
            dataKey={dataKey}
            nameKey={nameKey}
            innerRadius={innerRadius}
            outerRadius={outerRadius}
            paddingAngle={data.length > 1 ? 2 : 0}
          >
            {data.map((_, index) => (
              <Cell key={index} fill={getChartColor(index)} stroke="var(--card)" strokeWidth={2} />
            ))}
          </Pie>
        </RechartsPieChart>
      </ResponsiveContainer>
    </div>
  );
}
