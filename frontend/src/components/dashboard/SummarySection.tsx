import type { ReactNode } from "react";

import { SectionHeader } from "@/components/layout/section-header";
import { cn } from "@/lib/utils";

export interface SummarySectionProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

/** A titled section of a Dashboard page's body — the Dashboard-context counterpart of `ReportSection`, sharing the same `SectionHeader` composition. */
export function SummarySection({ title, description, actions, children, className }: SummarySectionProps) {
  return (
    <section className={cn("space-y-4", className)}>
      <SectionHeader title={title} description={description} actions={actions} />
      {children}
    </section>
  );
}
