import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTitle } from "@/components/layout/page-title";

interface PageHeaderProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  /** e.g. a Status Badge, rendered beside the title. */
  badge?: ReactNode;
  /** Primary/Secondary action buttons, right-aligned. */
  actions?: ReactNode;
}

/**
 * Breadcrumb + `PageTitle`, per 06_COMPONENT_LIBRARY.md §1 /
 * 05_PAGE_CATALOG.md §0's Global Layout Standard. Breadcrumbs no-ops on the
 * Dashboard and on bare List pages, per 03_INFORMATION_ARCHITECTURE.md §7 —
 * callers never need to suppress it. The title/badge/actions row itself is
 * `PageTitle` — not reimplemented here — so the two stay in sync by
 * construction.
 */
export function PageHeader({ title, description, icon, badge, actions }: PageHeaderProps) {
  return (
    <div className="space-y-3">
      <Breadcrumbs />
      <PageTitle title={title} subtitle={description} icon={icon} badge={badge} actions={actions} />
    </div>
  );
}
