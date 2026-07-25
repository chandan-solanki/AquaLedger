import type { ReactNode } from "react";

import { ActionBar } from "@/components/layout/action-bar";
import { ErrorState } from "@/components/feedback/error-state";
import { FormSkeleton } from "@/components/feedback/skeletons/form-skeleton";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { cn } from "@/lib/utils";

interface FormPageTemplateProps {
  title: string;
  description?: string;
  /** Edit forms load an existing record; Create forms have no server dependency and render immediately, per `05_PAGE_CATALOG.md` §0. */
  isLoading?: boolean;
  error?: { title: string; description?: string; onRetry?: () => void } | null;
  /** The form's own field groups, typically wrapped in one or more `ContentSection`s. */
  children: ReactNode;
  /** The Cancel/Save action row — left decoupled from `PageAction` since a real Save button needs `type="submit"` inside the owning `<form>`, not a generic click handler. */
  actions?: ReactNode;
  /** Pins `actions` to the bottom of the viewport — per `06_COMPONENT_LIBRARY.md` §1, only for forms long enough to outgrow one screen; short forms leave this off. */
  stickyActions?: boolean;
}

/**
 * The Form Page Template (Create/Edit), per `05_PAGE_CATALOG.md` §0: Page
 * Header → field content → action row. Deliberately narrower than
 * `PageContainer`'s list-page default, since a form's field groups read
 * better at a constrained width than stretched across a wide screen.
 */
export function FormPageTemplate({
  title,
  description,
  isLoading = false,
  error = null,
  children,
  actions,
  stickyActions = false,
}: FormPageTemplateProps) {
  return (
    <PageContainer className="max-w-3xl">
      <PageHeader title={title} description={description} />

      {error ? (
        <ErrorState title={error.title} description={error.description} onRetry={error.onRetry} />
      ) : isLoading ? (
        <FormSkeleton />
      ) : (
        children
      )}

      {actions && !error && (
        <div
          className={cn(
            stickyActions && "sticky bottom-0 -mx-4 border-t bg-background/95 px-4 py-3 backdrop-blur-sm md:-mx-6 md:px-6"
          )}
        >
          <ActionBar className="justify-end">{actions}</ActionBar>
        </div>
      )}
    </PageContainer>
  );
}
