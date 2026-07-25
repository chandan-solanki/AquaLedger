import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface FormSkeletonProps {
  fields?: number;
  className?: string;
}

/**
 * Placeholder field shapes matching an Edit page's field layout while the
 * existing record loads — Create pages have no server dependency and render
 * immediately, per `06_COMPONENT_LIBRARY.md` §12 / `05_PAGE_CATALOG.md` §0.
 */
export function FormSkeleton({ fields = 5, className }: FormSkeletonProps) {
  return (
    <div className={cn("space-y-5", className)} aria-hidden>
      {Array.from({ length: fields }).map((_, i) => (
        <div key={i} className="space-y-2">
          <Skeleton className="h-3.5 w-24" />
          <Skeleton className="h-9 w-full" />
        </div>
      ))}
      <div className="flex justify-end gap-2 pt-2">
        <Skeleton className="h-9 w-20" />
        <Skeleton className="h-9 w-24" />
      </div>
    </div>
  );
}
