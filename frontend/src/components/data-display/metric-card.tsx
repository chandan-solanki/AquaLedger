import type { LucideIcon } from "lucide-react";
import { Minus, TrendingDown, TrendingUp } from "lucide-react";
import type { ReactNode } from "react";

import { StatCardSkeleton } from "@/components/feedback/skeletons/stat-card-skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  title: string;
  /** Already formatted for display (e.g. via `formatCurrency`) — this component never formats values itself. */
  value: string;
  description?: ReactNode;
  icon?: LucideIcon;
  isLoading?: boolean;
  className?: string;
}

/**
 * A single labeled numeric value with tabular-numeral emphasis — the KPI/
 * Stat Card primitive, per `06_COMPONENT_LIBRARY.md` §9. Never formats or
 * fetches its own value; the caller (a future Dashboard/Report session
 * wired to real data) passes an already-formatted string, keeping this
 * component free of business/financial logic.
 */
export function MetricCard({ title, value, description, icon: Icon, isLoading, className }: MetricCardProps) {
  if (isLoading) return <StatCardSkeleton className={className} />;

  return (
    <Card className={className}>
      <CardHeader className="flex-row items-start justify-between gap-2 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        {Icon && <Icon className="size-4 text-muted-foreground" aria-hidden />}
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-semibold tabular-nums">{value}</p>
        {description && <div className="text-xs text-muted-foreground">{description}</div>}
      </CardContent>
    </Card>
  );
}

interface TrendMetricCardProps extends MetricCardProps {
  /** e.g. 12.4 or -3.2 — sign determines up/down when `trend` isn't given explicitly. */
  changePercentage?: number;
  trend?: "up" | "down" | "neutral";
  /** e.g. "vs last period" — what the change is relative to. */
  comparisonLabel?: string;
}

const TREND_ICON = { up: TrendingUp, down: TrendingDown, neutral: Minus } as const;

/**
 * `MetricCard` plus a period-over-period change indicator, per
 * `06_COMPONENT_LIBRARY.md` §9's Trend Card. Colors this deliberately
 * without a "success" green — `globals.css` doesn't define a Success token
 * yet (flagged in the Session 4 README) — a down trend uses the existing
 * `destructive` token, an up/neutral trend stays neutral foreground rather
 * than inventing an undeclared color.
 */
export function TrendMetricCard({
  changePercentage,
  trend,
  comparisonLabel = "vs last period",
  description,
  ...metricCardProps
}: TrendMetricCardProps) {
  if (metricCardProps.isLoading) return <StatCardSkeleton className={metricCardProps.className} />;

  const resolvedTrend =
    trend ?? (changePercentage === undefined ? undefined : changePercentage > 0 ? "up" : changePercentage < 0 ? "down" : "neutral");
  const TrendIcon = resolvedTrend ? TREND_ICON[resolvedTrend] : undefined;

  const trendDescription =
    changePercentage === undefined ? (
      description
    ) : (
      <span className={cn("inline-flex items-center gap-1", resolvedTrend === "down" && "text-destructive")}>
        {TrendIcon && <TrendIcon className="size-3" aria-hidden />}
        {Math.abs(changePercentage)}% {comparisonLabel}
      </span>
    );

  return <MetricCard {...metricCardProps} description={trendDescription} />;
}
