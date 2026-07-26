import { BarChart3 } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { EmptyState } from "@/components/feedback/empty-state";
import { cn } from "@/lib/utils";

export interface ChartEmptyProps {
  icon?: LucideIcon;
  title?: string;
  description?: string;
  height?: number;
  className?: string;
}

/** A chart's Empty State — "no data for this period/filter," distinct from `ChartError`'s "the data failed to load," per the same distinction `DataTableEmpty`/`DataTableNoResults` draw for tables. */
export function ChartEmpty({
  icon = BarChart3,
  title = "No data to display",
  description,
  height = 300,
  className,
}: ChartEmptyProps) {
  return (
    <div className={cn("flex items-center justify-center", className)} style={{ height }}>
      <EmptyState icon={icon} title={title} description={description} />
    </div>
  );
}
