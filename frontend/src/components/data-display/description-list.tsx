import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface DescriptionItem {
  term: string;
  details: ReactNode;
}

interface DescriptionListProps {
  items: DescriptionItem[];
  className?: string;
}

/**
 * A row-per-item term/details list (label left, value right, divided
 * rows) — the traditional "definition list" reading pattern, distinct from
 * `KeyValueList`'s stacked-card grid: use this for a linear read-top-to-
 * bottom summary (a Settings page's read-only configuration recap, an
 * Audit entry's field list); use `KeyValueList` for an Overview Card's
 * scannable field grid. Both render semantic `<dl>` markup — this one's
 * layout is what differs, not its accessibility contract.
 */
export function DescriptionList({ items, className }: DescriptionListProps) {
  return (
    <dl className={cn("divide-y divide-border", className)}>
      {items.map((item) => (
        <div key={item.term} className="flex items-start justify-between gap-4 py-3 first:pt-0 last:pb-0">
          <dt className="text-sm text-muted-foreground">{item.term}</dt>
          <dd className="text-right text-sm font-medium text-foreground">{item.details}</dd>
        </div>
      ))}
    </dl>
  );
}
