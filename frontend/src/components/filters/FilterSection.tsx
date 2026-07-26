import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface FilterSectionProps {
  title?: string;
  description?: string;
  children: ReactNode;
  className?: string;
}

/**
 * Divides a `FilterPanel`/`AdvancedFilter`'s body into labeled blocks (e.g.
 * "Status," "Date Range") — the filter-context sibling of `components/form`'s
 * `FormSection`, sized for a denser, sidebar-style layout rather than a
 * full-page form.
 */
export function FilterSection({ title, description, children, className }: FilterSectionProps) {
  return (
    <div className={cn("space-y-2.5", className)}>
      {title && (
        <div>
          <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            {title}
          </h4>
          {description && <p className="text-xs text-muted-foreground">{description}</p>}
        </div>
      )}
      {children}
    </div>
  );
}
