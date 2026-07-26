import type { ReactNode } from "react";

import { SectionHeader } from "@/components/layout/section-header";
import { cn } from "@/lib/utils";

export interface FormSectionProps {
  title?: string;
  description?: string;
  children: ReactNode;
  className?: string;
}

/**
 * Divides a form's field groups, per `06_COMPONENT_LIBRARY.md` §1 — composes
 * the existing `SectionHeader` layout primitive rather than reimplementing
 * a title/description row, per the reuse-over-duplication rule in
 * `06_COMPONENT_LIBRARY.md` §19.
 */
export function FormSection({ title, description, children, className }: FormSectionProps) {
  return (
    <div className={cn("space-y-4", className)}>
      {title && <SectionHeader title={title} description={description} />}
      {children}
    </div>
  );
}
