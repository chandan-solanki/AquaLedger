import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface SidebarSkeletonProps {
  groups?: number;
  itemsPerGroup?: number;
  className?: string;
}

/**
 * Mirrors AppSidebar's brand + grouped-item shape. Not currently wired into
 * the live Sidebar (its content is derived synchronously from the already-
 * resolved session, so it never suspends) — reserved for a future role- or
 * server-driven navigation source that would need one.
 */
export function SidebarSkeleton({ groups = 3, itemsPerGroup = 3, className }: SidebarSkeletonProps) {
  return (
    <div className={cn("flex h-full w-64 flex-col gap-6 border-r p-3", className)} aria-hidden>
      <div className="flex items-center gap-2 px-1 py-2">
        <Skeleton className="size-6 rounded-md" />
        <Skeleton className="h-4 w-24" />
      </div>
      {Array.from({ length: groups }).map((_, groupIndex) => (
        <div key={groupIndex} className="space-y-2">
          <Skeleton className="h-3 w-16" />
          {Array.from({ length: itemsPerGroup }).map((_, itemIndex) => (
            <div key={itemIndex} className="flex items-center gap-2 px-1 py-1.5">
              <Skeleton className="size-4 shrink-0 rounded-sm" />
              <Skeleton className="h-3.5 w-full max-w-32" />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
