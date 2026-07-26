import { cn } from "@/lib/utils";

export interface PaginationSummaryProps {
  /** 1-based current page. */
  page: number;
  pageSize: number;
  totalCount: number;
  className?: string;
}

/**
 * The total-count display paired with every paginated table/list, per
 * `02_DESIGN_SYSTEM.md` §9 — "showing 1–50 of 240" gives financial data a
 * countable, citable boundary. Computes `from`/`to` itself from
 * `page`/`pageSize`/`totalCount` so every call site renders identical text
 * for identical inputs.
 */
export function PaginationSummary({ page, pageSize, totalCount, className }: PaginationSummaryProps) {
  const from = totalCount === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(totalCount, page * pageSize);

  return (
    <p className={cn("text-sm text-muted-foreground", className)} role="status">
      {totalCount === 0 ? "No results" : `Showing ${from}–${to} of ${totalCount}`}
    </p>
  );
}
