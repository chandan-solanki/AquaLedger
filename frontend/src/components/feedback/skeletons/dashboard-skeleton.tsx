import { CardSkeleton } from "@/components/feedback/skeletons/card-skeleton";
import { StatCardSkeleton } from "@/components/feedback/skeletons/stat-card-skeleton";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * The Page Skeleton composition specific to the Dashboard's sections (KPIs,
 * Quick Actions, Recent Activity, Pending Work), per
 * `06_COMPONENT_LIBRARY.md` §12. Each section is shaped independently so a
 * future data-fetching Dashboard can resolve them behind independent
 * Suspense boundaries without this skeleton needing to change shape.
 */
export function DashboardSkeleton() {
  return (
    <div className="space-y-6" aria-hidden>
      <div className="space-y-2">
        <Skeleton className="h-6 w-56" />
        <Skeleton className="h-4 w-40" />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <StatCardSkeleton key={i} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <CardSkeleton className="lg:col-span-1" lines={3} />
        <CardSkeleton className="lg:col-span-2" lines={3} />
      </div>

      <CardSkeleton lines={3} />
    </div>
  );
}
