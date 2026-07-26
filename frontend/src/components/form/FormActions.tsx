import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface FormActionsProps {
  /** The form's single main action (Save, Issue) — `06_COMPONENT_LIBRARY.md` §3's "exactly one Primary Button" rule. */
  primary?: ReactNode;
  /** Supporting actions beside Primary (Cancel, Save Draft). */
  secondary?: ReactNode;
  /** A destructive action (Delete), kept visually separate from Primary/Secondary per `02_DESIGN_SYSTEM.md` §8. */
  danger?: ReactNode;
  /** Keeps the action row reachable without scrolling to the form's end, per `06_COMPONENT_LIBRARY.md` §1 Sticky Footer — reserved for forms whose content can exceed one viewport height. */
  sticky?: boolean;
  className?: string;
}

/**
 * The form's action row, per `06_COMPONENT_LIBRARY.md` §1/§8 — a consistent
 * placement for Primary/Secondary/Danger regardless of which form renders
 * it. Danger sits apart from Primary/Secondary (left vs. right) so a
 * destructive action is never grouped with — or mistaken for — the form's
 * routine Save/Cancel actions.
 */
export function FormActions({ primary, secondary, danger, sticky, className }: FormActionsProps) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center justify-between gap-3 border-t pt-4",
        sticky &&
          "sticky bottom-0 bg-background/95 backdrop-blur-sm supports-backdrop-filter:bg-background/80",
        className
      )}
    >
      <div className="flex items-center gap-2">{danger}</div>
      <div className="flex flex-wrap items-center gap-2">
        {secondary}
        {primary}
      </div>
    </div>
  );
}
