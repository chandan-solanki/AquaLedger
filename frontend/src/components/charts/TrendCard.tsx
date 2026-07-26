import { Minus, TrendingDown, TrendingUp } from "lucide-react";

import { cn } from "@/lib/utils";

export type TrendDirection = "positive" | "negative" | "neutral";

export interface TrendCardProps {
  /** Already formatted, e.g. "12.4%" — this component never computes or formats the number itself. */
  value: string;
  direction: TrendDirection;
  /** e.g. "vs last month" */
  label?: string;
  className?: string;
}

const TREND_ICON = { positive: TrendingUp, negative: TrendingDown, neutral: Minus } as const;

// `globals.css` doesn't define a "success" token — a positive/neutral trend
// deliberately stays neutral foreground rather than inventing an undeclared
// green; only "negative" borrows the existing `destructive` token. Mirrors
// the same decision already made for `TrendMetricCard` in
// `components/data-display/metric-card.tsx`.
const TREND_CLASS: Record<TrendDirection, string> = {
  positive: "text-foreground",
  negative: "text-destructive",
  neutral: "text-muted-foreground",
};

/** The small inline trend indicator (icon + change + comparison label) — used standalone, or embedded in `KpiCard`. */
export function TrendCard({ value, direction, label, className }: TrendCardProps) {
  const Icon = TREND_ICON[direction];

  return (
    <span className={cn("inline-flex items-center gap-1 text-xs font-medium", TREND_CLASS[direction], className)}>
      <Icon className="size-3.5" aria-hidden />
      {value}
      {label && <span className="font-normal text-muted-foreground">{label}</span>}
    </span>
  );
}
