import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface FormGridProps {
  /** Column count at the widest breakpoint; collapses toward 1 column below the laptop breakpoint, per `02_DESIGN_SYSTEM.md` §15. */
  columns?: 1 | 2 | 3 | 4;
  children: ReactNode;
  className?: string;
}

/**
 * The general-purpose responsive grid underlying every form's field layout,
 * per `06_COMPONENT_LIBRARY.md` §25 / `02_DESIGN_SYSTEM.md` §5's Form
 * Spacing rules — multi-column above the laptop breakpoint, single column
 * below it. A field that should span every column regardless of `columns`
 * (a full-width Textarea, say) takes `className="md:col-span-full"` at the
 * call site rather than this component special-casing it.
 */
export function FormGrid({ columns = 2, children, className }: FormGridProps) {
  return (
    <div
      className={cn(
        "grid grid-cols-1 gap-x-4 gap-y-5",
        columns >= 2 && "md:grid-cols-2",
        columns >= 3 && "lg:grid-cols-3",
        columns >= 4 && "xl:grid-cols-4",
        className
      )}
    >
      {children}
    </div>
  );
}
