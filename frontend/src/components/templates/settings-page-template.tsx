import type { ReactNode } from "react";

import { FormPageTemplate } from "@/components/templates/form-page-template";

interface SettingsPageTemplateProps {
  title: string;
  description?: string;
  isLoading?: boolean;
  error?: { title: string; description?: string; onRetry?: () => void } | null;
  children: ReactNode;
  actions?: ReactNode;
}

/**
 * Settings pages are single-record configuration forms with no List/Detail
 * split, per `05_PAGE_CATALOG.md` §14 — the same shape as
 * `FormPageTemplate`, so it's composed rather than reimplemented (per this
 * session's "do not duplicate layout logic" requirement). A distinct
 * component still earns its place per `06_COMPONENT_LIBRARY.md` §19: it
 * fixes the narrower, read-mostly conventions Settings pages share (no
 * sticky footer — these are short, single-section forms) so a future
 * Settings page never has to think about `FormPageTemplate`'s
 * business-transaction-oriented options (like `stickyActions`).
 */
export function SettingsPageTemplate({ title, description, isLoading, error, children, actions }: SettingsPageTemplateProps) {
  return (
    <FormPageTemplate title={title} description={description} isLoading={isLoading} error={error} actions={actions}>
      {children}
    </FormPageTemplate>
  );
}
