import { format } from "date-fns";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { PageTitle } from "@/components/layout/page-title";
import { DEFAULT_DATETIME_FORMAT } from "@/lib/date-format";
import { cn } from "@/lib/utils";

export interface ReportHeaderProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  actions?: ReactNode;
  /** Rendered as "Generated {date}" beneath the title row — a report's own freshness marker. */
  generatedAt?: Date;
  className?: string;
}

/** A Report page's title row — composes the shared `PageTitle` (no separate title/actions layout to keep in sync) plus an optional "Generated at" freshness caption specific to reports. */
export function ReportHeader({ title, description, icon, actions, generatedAt, className }: ReportHeaderProps) {
  return (
    <div className={cn("space-y-1", className)}>
      <PageTitle title={title} subtitle={description} icon={icon} actions={actions} />
      {generatedAt && (
        <p className="text-xs text-muted-foreground">Generated {format(generatedAt, DEFAULT_DATETIME_FORMAT)}</p>
      )}
    </div>
  );
}
