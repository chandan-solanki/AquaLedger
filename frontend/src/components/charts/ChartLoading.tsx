import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export interface ChartLoadingProps {
  height?: number;
  className?: string;
}

// Fixed, not random — a random per-render height would cause a hydration
// mismatch between the server-rendered skeleton and the client's first paint.
const BAR_HEIGHTS = [55, 80, 40, 95, 65, 45, 75, 60, 90, 50, 70, 85];

/** A chart's Loading State — a bar-shaped skeleton at the chart's own height, so the surrounding `ChartCard`/layout doesn't reflow once real data arrives. */
export function ChartLoading({ height = 300, className }: ChartLoadingProps) {
  return (
    <div className={cn("flex w-full items-end gap-2 px-2", className)} style={{ height }} aria-hidden>
      {BAR_HEIGHTS.map((barHeight, index) => (
        <Skeleton key={index} className="flex-1 rounded-t-sm rounded-b-none" style={{ height: `${barHeight}%` }} />
      ))}
    </div>
  );
}
