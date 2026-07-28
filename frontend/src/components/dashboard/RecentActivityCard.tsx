import { History } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { EmptyState } from "@/components/feedback/empty-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export interface RecentActivityItem {
  id: string;
  title: string;
  description?: string;
  /** Already formatted for display (e.g. "2 hours ago") — this component never computes relative time itself. */
  timestamp: string;
  icon?: LucideIcon;
  /** e.g. a type Badge, rendered beside the title. */
  badge?: ReactNode;
}

export interface RecentActivityCardProps {
  title?: string;
  items: RecentActivityItem[];
  isLoading?: boolean;
  emptyMessage?: string;
  /** Hard-truncates to this many items. Ignored when `scrollable` is set — the list scrolls instead of being cut off. */
  maxItems?: number;
  /** Wraps the list in a fixed-height scroll region instead of hard-truncating to `maxItems`, for a feed the backend already bounds itself (e.g. "last 10"). */
  scrollable?: boolean;
  /** Scroll region height in pixels — only relevant when `scrollable` is set. */
  maxHeight?: number;
  className?: string;
}

/** The Dashboard's recent-activity feed card — a list of already-prepared activity entries, with its own loading skeleton and empty state. */
export function RecentActivityCard({
  title = "Recent Activity",
  items,
  isLoading,
  emptyMessage = "No recent activity",
  maxItems = 5,
  scrollable = false,
  maxHeight = 360,
  className,
}: RecentActivityCardProps) {
  const visibleItems = scrollable ? items : items.slice(0, maxItems);

  const list = (
    <ul className="space-y-4">
      {visibleItems.map((item) => {
        const Icon = item.icon ?? History;
        return (
          <li key={item.id} className="flex items-start gap-3">
            <span className={cn("flex size-8 shrink-0 items-center justify-center rounded-full border bg-muted")}>
              <Icon className="size-4 text-muted-foreground" aria-hidden />
            </span>
            <div className="min-w-0 flex-1 space-y-0.5">
              <div className="flex items-center justify-between gap-2">
                <p className="truncate text-sm font-medium">{item.title}</p>
                {item.badge}
              </div>
              {item.description && (
                <p className="truncate text-xs text-muted-foreground">{item.description}</p>
              )}
              <p className="text-xs text-muted-foreground">{item.timestamp}</p>
            </div>
          </li>
        );
      })}
    </ul>
  );

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
        ) : scrollable ? (
          <ScrollArea style={{ height: maxHeight }} className="pr-3">
            {list}
          </ScrollArea>
        ) : (
          list
        )}
      </CardContent>
    </Card>
  );
}
