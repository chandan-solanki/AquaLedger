import { ChartLoading } from "@/components/charts";
import { CardSkeleton } from "@/components/feedback/skeletons/card-skeleton";
import { StatCardSkeleton } from "@/components/feedback/skeletons/stat-card-skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

/** A `ChartCard`-shaped placeholder (title/description bars + a bar-shaped `ChartLoading` body) for the charts row - matches `ChartCard`'s own `isLoading` rendering so nothing shifts once real chart data arrives. */
function ChartCardSkeleton() {
  return (
    <Card aria-hidden>
      <CardHeader className="gap-2">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-3 w-48" />
      </CardHeader>
      <CardContent>
        <ChartLoading height={300} />
      </CardContent>
    </Card>
  );
}

/**
 * The Page Skeleton composition specific to the Dashboard's sections, per
 * `06_COMPONENT_LIBRARY.md` §12 — reshaped for TASKS.md Sprint 10's real
 * layout (Header → 8-card KPI row → charts row (monthly sales, monthly
 * purchases, fish sales, trip status) → Session 4's widgets row (top
 * customers/suppliers/fish, outstanding summary) → Operations/Financial →
 * Recent Activity/Alerts; Quick Actions moved into the header, not a body
 * section) so the initial-load placeholder matches the real page's shape
 * exactly and nothing shifts once data arrives.
 */
export function DashboardSkeleton() {
  return (
    <div className="space-y-6" aria-hidden>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-2">
          <Skeleton className="h-6 w-40" />
          <Skeleton className="h-4 w-56" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="size-8 rounded-md" />
          <Skeleton className="h-8 w-32 rounded-md" />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <StatCardSkeleton key={i} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <ChartCardSkeleton key={i} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <CardSkeleton key={i} lines={4} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <CardSkeleton lines={4} />
        <CardSkeleton lines={4} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <CardSkeleton lines={4} />
        <CardSkeleton lines={4} />
      </div>
    </div>
  );
}
