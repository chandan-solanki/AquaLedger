"use client";

import type { DefaultLegendContentProps } from "recharts";

import { cn } from "@/lib/utils";

export interface LegendProps extends Pick<DefaultLegendContentProps, "payload"> {
  className?: string;
}

/**
 * The shared custom legend every chart in this folder passes to Recharts'
 * `<Legend content={...} />` — themed off design-system tokens instead of
 * the library's default inline styling. Recharts clones this element and
 * injects `payload` (one entry per series/slice) at render time.
 */
export function Legend({ payload, className }: LegendProps) {
  if (!payload || payload.length === 0) return null;

  return (
    <ul className={cn("flex flex-wrap items-center justify-center gap-x-4 gap-y-1.5 pt-2 text-xs", className)}>
      {payload.map((entry, index) => (
        <li key={index} className="flex items-center gap-1.5 text-muted-foreground">
          <span className="size-2.5 rounded-full" style={{ backgroundColor: entry.color }} aria-hidden />
          {entry.value}
        </li>
      ))}
    </ul>
  );
}
