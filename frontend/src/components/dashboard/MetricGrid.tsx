import type { ComponentProps } from "react";

import { SummaryGrid } from "@/components/data-display/summary-grid";

export type MetricGridProps = ComponentProps<typeof SummaryGrid>;

/** The Dashboard's KPI row — a direct alias of `SummaryGrid` (also used by Reports/Detail pages) so the "N-column KPI grid that reflows on narrow screens" layout has exactly one implementation across the app. */
export function MetricGrid(props: MetricGridProps) {
  return <SummaryGrid {...props} />;
}
