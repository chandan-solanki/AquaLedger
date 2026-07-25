import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

/**
 * The generic Empty State primitive (`06_COMPONENT_LIBRARY.md` §13):
 * purposeful and action-oriented, not just blank space. Every module's own
 * "No {Entity}" List page empty state (Sprint 4+) configures this directly
 * with its own icon/copy/Primary CTA rather than each module building a
 * separate component, per the doc's explicit "one pattern, per-module copy"
 * rule.
 *
 * `role="status"` announces the empty result to assistive technology once
 * data has resolved, distinguishing "confirmed empty" from "still loading."
 */
export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      role="status"
      className={cn(
        "flex flex-col items-center gap-3 py-12 text-center text-muted-foreground",
        className
      )}
    >
      {Icon && <Icon className="size-9" aria-hidden />}
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">{title}</p>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {action}
    </div>
  );
}
