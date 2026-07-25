import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { TableSkeleton } from "@/components/feedback/skeletons/table-skeleton";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { PageActions, type PageAction } from "@/components/layout/page-actions";
import { PageToolbar } from "@/components/layout/page-toolbar";
import { ErrorState } from "@/components/feedback/error-state";

interface ListPageTemplateProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  badge?: ReactNode;
  primaryAction?: PageAction;
  secondaryActions?: PageAction[];
  /** The List page Toolbar's search/filter slots, typically a `FilterBar`/`TableToolbar`. */
  search?: ReactNode;
  filters?: ReactNode;
  isLoading?: boolean;
  error?: { title: string; description?: string; onRetry?: () => void } | null;
  isEmpty?: boolean;
  emptyState?: ReactNode;
  /** The Enterprise Data Table (Sprint 2+) or any other list content. */
  children: ReactNode;
}

/**
 * The List Page Template, per `05_PAGE_CATALOG.md` §0: Page Header → List
 * Toolbar → content area, full-width (the deliberate exception to
 * `PageContainer`'s max-width, per `06_COMPONENT_LIBRARY.md` §1). Owns the
 * Loading/Empty/Error state switch so every future List module gets the
 * "all four states defined explicitly" rule (`02_DESIGN_SYSTEM.md` §8) for
 * free instead of reimplementing it per module. Does not render a table
 * itself — that's the Enterprise Data Table, built in a future session;
 * `children` is whatever content the module provides once loaded.
 */
export function ListPageTemplate({
  title,
  description,
  icon,
  badge,
  primaryAction,
  secondaryActions,
  search,
  filters,
  isLoading = false,
  error = null,
  isEmpty = false,
  emptyState,
  children,
}: ListPageTemplateProps) {
  return (
    <PageContainer fullWidth>
      <PageHeader
        title={title}
        description={description}
        icon={icon}
        badge={badge}
        actions={<PageActions primary={primaryAction} secondary={secondaryActions} />}
      />

      {(search || filters) && <PageToolbar search={search} filters={filters} />}

      {error ? (
        <ErrorState title={error.title} description={error.description} onRetry={error.onRetry} />
      ) : isLoading ? (
        <TableSkeleton />
      ) : isEmpty ? (
        emptyState
      ) : (
        children
      )}
    </PageContainer>
  );
}
