import type { ReactNode } from "react";

import { SectionHeader } from "@/components/layout/section-header";
import { cn } from "@/lib/utils";

interface ContentSectionProps {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

/**
 * Groups related content within a page's body, composing `SectionHeader`
 * (when a title is given) with consistent vertical rhythm — the smaller,
 * in-page sibling of `PageContainer`'s whole-page wrapper, per
 * `06_COMPONENT_LIBRARY.md` §1's Section Header entry.
 */
export function ContentSection({ title, description, actions, children, className }: ContentSectionProps) {
  return (
    <section className={cn("space-y-4", className)}>
      {title && <SectionHeader title={title} description={description} actions={actions} />}
      {children}
    </section>
  );
}
