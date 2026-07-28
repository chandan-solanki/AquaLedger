import { AlertTriangle, CheckCircle2 } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { EmptyState } from "@/components/feedback/empty-state";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export interface AlertsCardItem {
  id: string;
  message: string;
  count: number;
  icon?: LucideIcon;
  /** `critical` reads as destructive (red), `advisory` as neutral — see `ALERT_TYPE_SEVERITY`'s own doc comment for why only two tiers exist. */
  severity?: "critical" | "advisory";
}

export interface AlertsCardProps {
  title?: string;
  items: AlertsCardItem[];
  isLoading?: boolean;
  emptyMessage?: string;
  className?: string;
  /** Wraps the list in a fixed-height scroll region once there's enough content to warrant it. */
  maxHeight?: number;
}

const SEVERITY_ICON_CLASS: Record<NonNullable<AlertsCardItem["severity"]>, string> = {
  critical: "text-destructive",
  advisory: "text-muted-foreground",
};

const SEVERITY_BADGE_VARIANT: Record<NonNullable<AlertsCardItem["severity"]>, "destructive" | "secondary"> = {
  critical: "destructive",
  advisory: "secondary",
};

/**
 * The Dashboard's alerts feed card — priority-colored, grouped-by-severity
 * list of already-computed alert counts (never invented client-side, per
 * this sprint's backend: only real, backend-supported alert types ever
 * appear here). Mirrors `RecentActivityCard`'s shape (loading skeleton,
 * empty state, optional scroll region) so the two feed cards read as one
 * system.
 */
export function AlertsCard({
  title = "Alerts",
  items,
  isLoading,
  emptyMessage = "No alerts — everything's on track",
  className,
  maxHeight = 320,
}: AlertsCardProps) {
  const list = (
    <ul className="space-y-3">
      {items.map((item) => {
        const Icon = item.icon ?? AlertTriangle;
        const severity = item.severity ?? "advisory";
        return (
          <li key={item.id} className="flex items-center gap-3">
            <span className="flex size-8 shrink-0 items-center justify-center rounded-full border bg-muted">
              <Icon className={cn("size-4", SEVERITY_ICON_CLASS[severity])} aria-hidden />
            </span>
            <p className="min-w-0 flex-1 truncate text-sm font-medium">{item.message}</p>
            <Badge variant={SEVERITY_BADGE_VARIANT[severity]} className="tabular-nums">
              {item.count}
            </Badge>
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
                <Skeleton className="h-3.5 flex-1" />
                <Skeleton className="h-5 w-8 rounded-full" />
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <EmptyState icon={CheckCircle2} title={emptyMessage} />
        ) : items.length > 4 ? (
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
