import type { ReactNode } from "react";

import { ErrorState } from "@/components/feedback/error-state";
import { NoReports } from "@/components/feedback/empty-states";
import { CardSkeleton } from "@/components/feedback/skeletons/card-skeleton";
import { PageActions, type PageAction } from "@/components/layout/page-actions";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";

interface ReportPageTemplateProps {
  title: string;
  description?: string;
  secondaryActions?: PageAction[];
  /** The report's Export dropdown (`ExportMenu`), rendered left of the secondary actions - TASKS.md Sprint 11 Session 5 Phase B. */
  exportMenu?: ReactNode;
  /** The report's Filter Bar (Date Range, Company/Supplier, ...), per `05_PAGE_CATALOG.md` §12. */
  filters?: ReactNode;
  /** The Summary KPI row — typically a `SummaryGrid` of `MetricCard`s. */
  summary?: ReactNode;
  /** Reports with 9+ columns (Trip/Boat Profitability, Fish Sales Analytics) print in landscape - TASKS.md Sprint 11 Session 5 Phase D, matching the PDF exporter's own `_LANDSCAPE_COLUMN_THRESHOLD`. */
  wide?: boolean;
  isLoading?: boolean;
  error?: { title: string; description?: string; onRetry?: () => void } | null;
  isEmpty?: boolean;
  /** Defaults to the "Coming Soon" empty state — most reports have no real data source until Sprint 3's reporting endpoints exist. */
  emptyState?: ReactNode;
  /** The results table and/or chart. */
  children: ReactNode;
}

/**
 * The Report Page Template, per `05_PAGE_CATALOG.md` §12: every report page
 * shares Filter Bar → Summary KPIs → Results → Export shape. Full-width
 * like List pages, since report results are equally table/chart-dense.
 */
export function ReportPageTemplate({
  title,
  description,
  secondaryActions,
  exportMenu,
  filters,
  summary,
  wide = false,
  isLoading = false,
  error = null,
  isEmpty = false,
  emptyState,
  children,
}: ReportPageTemplateProps) {
  return (
    <PageContainer fullWidth className={wide ? "report-print-landscape" : undefined}>
      <PageHeader
        title={title}
        description={description}
        actions={
          <>
            {exportMenu}
            <PageActions secondary={secondaryActions} />
          </>
        }
      />

      {filters && <div data-slot="report-filters">{filters}</div>}
      {summary}

      {error ? (
        <ErrorState title={error.title} description={error.description} onRetry={error.onRetry} />
      ) : isLoading ? (
        <CardSkeleton lines={5} />
      ) : isEmpty ? (
        (emptyState ?? <NoReports />)
      ) : (
        children
      )}
    </PageContainer>
  );
}
