"use client";

import { PieChart, type PieChartProps } from "./PieChart";

export type DonutChartProps = PieChartProps;

/** A `PieChart` with a donut hole pre-configured — same series/tooltip/legend/loading/empty/error behavior, just a non-zero default `innerRadius`. */
export function DonutChart({ innerRadius = "60%", ...props }: DonutChartProps) {
  return <PieChart {...props} innerRadius={innerRadius} />;
}
