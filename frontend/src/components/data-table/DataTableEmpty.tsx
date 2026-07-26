import { Inbox } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { EmptyState } from "@/components/feedback/empty-state";

export interface DataTableEmptyProps {
  icon?: LucideIcon;
  title?: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

/**
 * "No records at all" — the table has genuinely zero rows for this tenant,
 * distinct from `DataTableNoResults`'s "no matches for the current
 * filter/search," per `04_USER_FLOWS.md` §21 and
 * `06_COMPONENT_LIBRARY.md` §13. Composes the shared `EmptyState` primitive
 * rather than reimplementing it; each feature module configures its own
 * icon/copy/"+ New {Entity}" action when it wires this table up.
 */
export function DataTableEmpty({
  icon = Inbox,
  title = "No records yet",
  description,
  action,
  className,
}: DataTableEmptyProps) {
  return (
    <EmptyState icon={icon} title={title} description={description} action={action} className={className} />
  );
}
