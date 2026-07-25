import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface PageToolbarProps {
  title?: string;
  description?: string;
  search?: ReactNode;
  filters?: ReactNode;
  actions?: ReactNode;
  secondaryActions?: ReactNode;
  className?: string;
}

/**
 * The row directly below a List page's header: Search + Filters on the
 * left, Primary CTA (and Secondary CTAs) on the right, per
 * `05_PAGE_CATALOG.md` §0's Global Layout Standard and
 * `02_DESIGN_SYSTEM.md` §8 Action Bar standard. Self-contained (an optional
 * local `title`/`description` rather than requiring `PageHeader`) so it can
 * also serve as a smaller in-page toolbar — a Card's own action row —
 * without a full page header.
 */
export function PageToolbar({
  title,
  description,
  search,
  filters,
  actions,
  secondaryActions,
  className,
}: PageToolbarProps) {
  const hasTitle = title || description;
  const hasControls = search || filters || actions || secondaryActions;

  if (!hasTitle && !hasControls) return null;

  return (
    <div className={cn("flex flex-wrap items-center justify-between gap-3", className)}>
      {hasTitle && (
        <div className="space-y-0.5">
          {title && <h2 className="text-sm font-semibold">{title}</h2>}
          {description && <p className="text-sm text-muted-foreground">{description}</p>}
        </div>
      )}
      {hasControls && (
        <div className="flex flex-1 flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            {search}
            {filters}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {secondaryActions}
            {actions}
          </div>
        </div>
      )}
    </div>
  );
}
