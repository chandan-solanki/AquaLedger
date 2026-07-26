import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export interface FilterBadgeProps {
  count: number;
  className?: string;
}

/**
 * A compact active-filter-count indicator for a Filters trigger button.
 * Renders nothing at `count <= 0` — an inactive filter set shows no badge
 * at all, rather than a hollow "0".
 */
export function FilterBadge({ count, className }: FilterBadgeProps) {
  if (count <= 0) return null;

  return (
    <Badge
      variant="default"
      className={cn("h-5 min-w-5 justify-center rounded-full px-1 tabular-nums", className)}
    >
      {count}
    </Badge>
  );
}
