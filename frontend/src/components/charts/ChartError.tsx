import { ErrorState } from "@/components/feedback/error-state";
import { cn } from "@/lib/utils";

export interface ChartErrorProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  height?: number;
  className?: string;
}

/** A chart's Error State — composes the shared `ErrorState` primitive, at the chart's own height so the surrounding layout doesn't reflow. */
export function ChartError({
  title = "Couldn't load this chart",
  description,
  onRetry,
  height = 300,
  className,
}: ChartErrorProps) {
  return (
    <div className={cn("flex items-center justify-center", className)} style={{ height }}>
      <ErrorState title={title} description={description} onRetry={onRetry} />
    </div>
  );
}
