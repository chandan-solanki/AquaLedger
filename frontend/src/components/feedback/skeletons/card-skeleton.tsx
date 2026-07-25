import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface CardSkeletonProps {
  /** Number of body lines to show beneath the title. */
  lines?: number;
  className?: string;
}

/** Placeholder shape for any Card variant while its content resolves (06_COMPONENT_LIBRARY.md §12). */
export function CardSkeleton({ lines = 2, className }: CardSkeletonProps) {
  return (
    <Card className={cn(className)} aria-hidden>
      <CardHeader>
        <Skeleton className="h-4 w-1/3" />
      </CardHeader>
      <CardContent className="space-y-2">
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton key={i} className="h-3.5 w-full last:w-2/3" />
        ))}
      </CardContent>
    </Card>
  );
}
