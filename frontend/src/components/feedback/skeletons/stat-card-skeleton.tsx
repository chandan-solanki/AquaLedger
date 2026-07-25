import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface StatCardSkeletonProps {
  className?: string;
}

/** Placeholder shape for a KPI/Stat Card's label + large value (06_COMPONENT_LIBRARY.md §9, §12). */
export function StatCardSkeleton({ className }: StatCardSkeletonProps) {
  return (
    <Card className={cn(className)} aria-hidden>
      <CardHeader className="pb-2">
        <Skeleton className="h-3.5 w-2/3" />
      </CardHeader>
      <CardContent className="space-y-1.5">
        <Skeleton className="h-7 w-1/2" />
        <Skeleton className="h-3 w-1/3" />
      </CardContent>
    </Card>
  );
}
