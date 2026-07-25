import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface KeyValueItem {
  label: string;
  value: ReactNode;
}

interface KeyValueListProps {
  items: KeyValueItem[];
  columns?: 1 | 2 | 3;
  className?: string;
}

const COLUMN_CLASSES: Record<NonNullable<KeyValueListProps["columns"]>, string> = {
  1: "",
  2: "sm:grid-cols-2",
  3: "sm:grid-cols-2 lg:grid-cols-3",
};

/**
 * A grid of stacked label/value pairs — an Overview Card's record fields
 * (name, status, key identifiers), per `05_PAGE_CATALOG.md` §0's Detail
 * Page Template. Uses `<dl>`/`<dt>`/`<dd>` so assistive technology announces
 * the label/value relationship, not just visual proximity.
 */
export function KeyValueList({ items, columns = 1, className }: KeyValueListProps) {
  return (
    <dl className={cn("grid gap-x-6 gap-y-4", COLUMN_CLASSES[columns], className)}>
      {items.map((item) => (
        <div key={item.label} className="space-y-0.5">
          <dt className="text-xs font-medium text-muted-foreground">{item.label}</dt>
          <dd className="text-sm text-foreground">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}
