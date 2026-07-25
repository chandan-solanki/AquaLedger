import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface SummaryGridProps {
  children: ReactNode;
  /** Column count at the widest breakpoint — reflows down (per `05_PAGE_CATALOG.md` §16) at every step below. */
  columns?: 2 | 3 | 4;
  className?: string;
}

const COLUMN_CLASSES: Record<NonNullable<SummaryGridProps["columns"]>, string> = {
  2: "sm:grid-cols-2",
  3: "sm:grid-cols-2 lg:grid-cols-3",
  4: "sm:grid-cols-2 lg:grid-cols-4",
};

/**
 * The responsive KPI-row grid underlying the Dashboard Grid and Report page
 * Summary KPI sections, per `06_COMPONENT_LIBRARY.md` §1 — reflows to
 * fewer columns rather than each page hand-rolling its own grid classes.
 */
export function SummaryGrid({ children, columns = 4, className }: SummaryGridProps) {
  return <div className={cn("grid grid-cols-1 gap-4", COLUMN_CLASSES[columns], className)}>{children}</div>;
}
