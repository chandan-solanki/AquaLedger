import type { ReactNode } from "react";

import { SectionHeader } from "@/components/layout/section-header";
import { cn } from "@/lib/utils";

export interface ReportSectionProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

/** A titled section within a Report page's body — composes the shared `SectionHeader`, same pattern as `FormSection`/`FilterSection`. */
export function ReportSection({ title, description, actions, children, className }: ReportSectionProps) {
  return (
    <section className={cn("space-y-4", className)}>
      <SectionHeader title={title} description={description} actions={actions} />
      {children}
    </section>
  );
}
