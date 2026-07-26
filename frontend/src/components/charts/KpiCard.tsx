import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

import { TrendCard, type TrendCardProps } from "./TrendCard";

export interface KpiCardProps {
  title: string;
  /** Already formatted for display (e.g. via `formatCurrency`) — this component never formats or computes the value itself. */
  value: string;
  subtitle?: ReactNode;
  icon?: LucideIcon;
  trend?: Pick<TrendCardProps, "value" | "direction" | "label">;
  isLoading?: boolean;
  className?: string;
}

/**
 * The Dashboard/Report KPI card — title, large value, optional icon,
 * optional trend indicator (composing `TrendCard` rather than re-deriving
 * its direction/icon logic), and a skeleton loading state. Shares its visual
 * shell with `components/data-display/metric-card.tsx`'s `MetricCard` by
 * design (same design-system Stat Card pattern) since this session's spec
 * places the chart-context version in its own folder; see this session's
 * Architecture Notes for the consolidation candidate this creates.
 */
export function KpiCard({ title, value, subtitle, icon: Icon, trend, isLoading, className }: KpiCardProps) {
  if (isLoading) {
    return (
      <Card className={className} aria-hidden>
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

  return (
    <Card className={className}>
      <CardHeader className="flex-row items-start justify-between gap-2 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        {Icon && <Icon className="size-4 text-muted-foreground" aria-hidden />}
      </CardHeader>
      <CardContent className="space-y-1">
        <p className="text-2xl font-semibold tabular-nums">{value}</p>
        {(trend || subtitle) && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {trend && <TrendCard {...trend} />}
            {subtitle}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
