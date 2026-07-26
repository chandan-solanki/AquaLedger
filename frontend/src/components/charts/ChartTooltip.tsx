"use client";

import type { ReactNode } from "react";
import type { TooltipContentProps } from "recharts";

import { cn } from "@/lib/utils";

export interface ChartTooltipProps extends Partial<TooltipContentProps> {
  labelFormatter?: (label: ReactNode) => ReactNode;
  valueFormatter?: (value: unknown, name: unknown) => ReactNode;
  className?: string;
}

/**
 * The shared custom tooltip content every chart in this folder passes to
 * Recharts' `<Tooltip content={...} />` — a themed replacement for the
 * library's default inline-styled tooltip, so it repaints correctly across
 * the light/dark class toggle. Recharts clones this element and injects
 * `active`/`payload`/`label` at render time; it is never rendered directly.
 */
export function ChartTooltip({
  active,
  payload,
  label,
  labelFormatter,
  valueFormatter,
  className,
}: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className={cn("min-w-32 rounded-md border bg-popover px-3 py-2 text-xs shadow-md", className)}>
      {label !== undefined && label !== null && (
        <p className="mb-1.5 font-medium text-popover-foreground">
          {labelFormatter ? labelFormatter(label) : label}
        </p>
      )}
      <ul className="space-y-1">
        {payload.map((entry, index) => (
          <li key={index} className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <span className="size-2 rounded-full" style={{ backgroundColor: entry.color }} aria-hidden />
              {entry.name}
            </span>
            <span className="font-medium tabular-nums text-popover-foreground">
              {valueFormatter ? valueFormatter(entry.value, entry.name) : String(entry.value)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
