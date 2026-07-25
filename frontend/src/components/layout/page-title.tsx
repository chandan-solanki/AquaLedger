import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface PageTitleProps {
  title: string;
  subtitle?: string;
  icon?: LucideIcon;
  /** e.g. a Status Badge, rendered beside the title. */
  badge?: ReactNode;
  /** Primary/Secondary action buttons, right-aligned. */
  actions?: ReactNode;
  className?: string;
}

/**
 * The title + optional icon/subtitle/badge/actions row — the reusable
 * primitive `PageHeader` composes for its own title row, and available
 * standalone anywhere a smaller title treatment is needed without a
 * breadcrumb (a Dialog header, a Card's own title region), per
 * `06_COMPONENT_LIBRARY.md` §1/§18's Page Header naming.
 */
export function PageTitle({ title, subtitle, icon: Icon, badge, actions, className }: PageTitleProps) {
  return (
    <div className={cn("flex flex-wrap items-start justify-between gap-3", className)}>
      <div className="flex items-start gap-3">
        {Icon && (
          <span className="flex size-9 shrink-0 items-center justify-center rounded-xl border bg-muted">
            <Icon className="size-4.5 text-muted-foreground" aria-hidden />
          </span>
        )}
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
            {badge}
          </div>
          {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}
