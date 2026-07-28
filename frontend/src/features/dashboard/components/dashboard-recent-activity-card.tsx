import { memo, useMemo } from "react";

import { RecentActivityCard } from "@/components/dashboard/RecentActivityCard";
import type { RecentActivityItem as SharedRecentActivityItem } from "@/components/dashboard/RecentActivityCard";
import { Badge } from "@/components/ui/badge";
import {
  ACTIVITY_TYPE_BADGE_VARIANT,
  ACTIVITY_TYPE_ICONS,
  ACTIVITY_TYPE_LABELS,
} from "@/features/dashboard/constants/activity-type";
import type { DashboardActivityItem } from "@/features/dashboard/types/dashboard";
import { formatRelativeTime } from "@/utils/format-date";

interface DashboardRecentActivityCardProps {
  items: DashboardActivityItem[];
  className?: string;
}

/**
 * Adapts the backend's five-source `recent_activity` feed (already merged,
 * sorted and limited to 10 server-side) into the shared `RecentActivityCard`
 * primitive's item shape — a type Badge and a per-type icon, per TASKS.md
 * Sprint 10 Session 2's "RECENT ACTIVITY" spec ("Icon / Badge / Timestamp /
 * Reference"). `scrollable` is used instead of a hard `maxItems` truncation
 * since the backend has already bounded the list to a sensible size.
 */
function DashboardRecentActivityCardImpl({ items, className }: DashboardRecentActivityCardProps) {
  const mapped = useMemo<SharedRecentActivityItem[]>(
    () =>
      items.map((item) => ({
        id: `${item.type}-${item.reference}-${item.createdAt}`,
        title: item.title,
        description: item.reference,
        timestamp: formatRelativeTime(item.createdAt),
        icon: ACTIVITY_TYPE_ICONS[item.type],
        badge: (
          <Badge variant={ACTIVITY_TYPE_BADGE_VARIANT[item.type]} className="shrink-0">
            {ACTIVITY_TYPE_LABELS[item.type]}
          </Badge>
        ),
      })),
    [items]
  );

  return (
    <RecentActivityCard
      title="Recent Activity"
      items={mapped}
      emptyMessage="Recent invoices, payments, and trip updates will appear here."
      scrollable
      maxHeight={380}
      className={className}
    />
  );
}

export const DashboardRecentActivityCard = memo(DashboardRecentActivityCardImpl);
