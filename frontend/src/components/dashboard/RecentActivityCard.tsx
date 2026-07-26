import { History } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { EmptyState } from "@/components/feedback/empty-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export interface RecentActivityItem {
  id: string;
  title: string;
  description?: string;
  /** Already formatted for display (e.g. "2 hours ago") — this component never computes relative time itself. */
  timestamp: string;
  icon?: LucideIcon;
}

export interface RecentActivityCardProps {
  title?: string;
  items: RecentActivityItem[];
  isLoading?: boolean;
  emptyMessage?: string;
  maxItems?: number;
  className?: string;
}

/** The Dashboard's recent-activity feed card — a fixed-length list of already-prepared activity entries, with its own loading skeleton and empty state. */
export function RecentActivityCard({
  title = "Recent Activity",
  items,
  isLoading,
  emptyMessage = "No recent activity",
  maxItems = 5,
  className,
}: RecentActivityCardProps) {
  const visibleItems = items.slice(0, maxItems);

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3" aria-hidden>
            {Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="flex items-center gap-3">
                <Skeleton className="size-8 shrink-0 rounded-full" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton className="h-3.5 w-3/4" />
                  <Skeleton className="h-3 w-1/3" />
                </div>
              </div>
            ))}
          </div>
        ) : visibleItems.length === 0 ? (
          <EmptyState icon={History} title={emptyMessage} />
        ) : (
          <ul className="space-y-4">
            {visibleItems.map((item) => {
              const Icon = item.icon ?? History;
              return (
                <li key={item.id} className="flex items-start gap-3">
                  <span className={cn("flex size-8 shrink-0 items-center justify-center rounded-full border bg-muted")}>
                    <Icon className="size-4 text-muted-foreground" aria-hidden />
                  </span>
                  <div className="min-w-0 flex-1 space-y-0.5">
                    <p className="truncate text-sm font-medium">{item.title}</p>
                    {item.description && (
                      <p className="truncate text-xs text-muted-foreground">{item.description}</p>
                    )}
                    <p className="text-xs text-muted-foreground">{item.timestamp}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
