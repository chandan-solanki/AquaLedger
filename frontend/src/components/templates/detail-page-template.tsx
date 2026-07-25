import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { ErrorState } from "@/components/feedback/error-state";
import { CardSkeleton } from "@/components/feedback/skeletons/card-skeleton";
import { PageActions, type PageAction } from "@/components/layout/page-actions";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";

interface DetailPageTemplateProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  badge?: ReactNode;
  primaryAction?: PageAction;
  secondaryActions?: PageAction[];
  isLoading?: boolean;
  /** A Not Found or a general load-failure — `05_PAGE_CATALOG.md` §0 distinguishes them by copy, not layout. */
  error?: { title: string; description?: string; onRetry?: () => void } | null;
  /** Overview Card + Related Records + Tabs + Timeline — whatever the record's own page composes. */
  children: ReactNode;
}

/**
 * The Detail Page Template, per `05_PAGE_CATALOG.md` §0: Page Header →
 * record content. No Empty State branch — "a Detail page only exists for a
 * record that exists" (per the same doc section); only Loading and Error
 * are handled here, Empty applies only to a Detail page's own Related
 * Records sub-tables, which is the owning module's concern, not this
 * template's.
 */
export function DetailPageTemplate({
  title,
  description,
  icon,
  badge,
  primaryAction,
  secondaryActions,
  isLoading = false,
  error = null,
  children,
}: DetailPageTemplateProps) {
  return (
    <PageContainer>
      <PageHeader
        title={title}
        description={description}
        icon={icon}
        badge={badge}
        actions={<PageActions primary={primaryAction} secondary={secondaryActions} />}
      />

      {error ? (
        <ErrorState title={error.title} description={error.description} onRetry={error.onRetry} />
      ) : isLoading ? (
        <div className="space-y-6">
          <CardSkeleton lines={4} />
          <CardSkeleton lines={3} />
        </div>
      ) : (
        children
      )}
    </PageContainer>
  );
}
