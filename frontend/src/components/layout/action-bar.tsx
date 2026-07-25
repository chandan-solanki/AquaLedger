import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface ActionBarProps {
  children: ReactNode;
  className?: string;
}

/**
 * A consistent row of action content — a dialog footer, a Toolbar's action
 * cluster, any spot needing a horizontally-arranged group of buttons, per
 * `02_DESIGN_SYSTEM.md` §8's Action Bar standard. Generic on purpose: for
 * the specific "one Primary Button plus supporting actions" page-header
 * convention, use `PageActions` instead.
 */
export function ActionBar({ children, className }: ActionBarProps) {
  return <div className={cn("flex flex-wrap items-center gap-2", className)}>{children}</div>;
}
