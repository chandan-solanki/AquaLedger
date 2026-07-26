import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface DashboardGridProps {
  children: ReactNode;
  className?: string;
}

/** The 12-column responsive grid a Dashboard page arranges its widgets on — reflows to a single column on narrow viewports. Each child controls its own width via its own `col-span-*`/`md:col-span-*`/`lg:col-span-*` className. */
export function DashboardGrid({ children, className }: DashboardGridProps) {
  return <div className={cn("grid grid-cols-1 gap-4 md:grid-cols-6 lg:grid-cols-12", className)}>{children}</div>;
}
