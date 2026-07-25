import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface ListSkeletonProps {
  rows?: number;
  className?: string;
}

/**
 * Placeholder for row-shaped (non-tabular) list content — Activity Feed,
 * Notification Panel — distinct from Table Skeleton's column structure,
 * per `06_COMPONENT_LIBRARY.md` §12.
 */
export function ListSkeleton({ rows = 4, className }: ListSkeletonProps) {
  return (
    <div className={cn("space-y-4", className)} aria-hidden>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-3">
          <Skeleton className="size-8 shrink-0 rounded-full" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-3.5 w-2/3" />
            <Skeleton className="h-3 w-1/3" />
          </div>
        </div>
      ))}
    </div>
  );
}
