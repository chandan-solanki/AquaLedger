/** The five design-system chart color tokens (`--chart-1`…`--chart-5` in globals.css), cycled for any series/slice count. */
export const CHART_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
] as const;

export function getChartColor(index: number): string {
  return CHART_COLORS[index % CHART_COLORS.length];
}

export interface ChartSeriesConfig {
  /** Key into each data row this series plots. */
  dataKey: string;
  /** Legend/tooltip label — defaults to `dataKey` when omitted. */
  label?: string;
  /** Defaults to a `CHART_COLORS` token, cycling by the series' position. */
  color?: string;
}

export type ChartDatum = Record<string, string | number | null>;
