import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { EmptyState } from "@/components/feedback/empty-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export interface DashboardMiniTableColumn<T> {
  key: string;
  header: string;
  align?: "left" | "right";
  render: (row: T) => ReactNode;
}

export interface DashboardMiniTableProps<T> {
  title: string;
  columns: DashboardMiniTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  /** Present only when a real destination route exists for a row — omit to render a plain (non-clickable) table, per TASKS.md Sprint 10 Session 4's "do not invent routes" rule. */
  onRowClick?: (row: T) => void;
  isLoading?: boolean;
  emptyIcon?: LucideIcon;
  emptyMessage: string;
  className?: string;
}

/**
 * A compact, read-only data table for Dashboard business-intelligence
 * widgets (Top Customers/Suppliers/Fish — TASKS.md Sprint 10 Session 4).
 * Deliberately not the full `components/data-table` (TanStack, pagination,
 * sorting, toolbar) — these widgets render a small, already-backend-sorted
 * top-N list with no client-side interaction beyond an optional row-click
 * drill-down, so a semantic `<table>` is all this needs. Mirrors
 * `RecentActivityCard`/`AlertsCard`'s own shape (title Card, loading
 * skeleton, empty state) so every Dashboard card reads as one system.
 */
export function DashboardMiniTable<T>({
  title,
  columns,
  rows,
  rowKey,
  onRowClick,
  isLoading,
  emptyIcon,
  emptyMessage,
  className,
}: DashboardMiniTableProps<T>) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3" aria-hidden>
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-8 w-full" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <EmptyState icon={emptyIcon} title={emptyMessage} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" aria-label={title}>
              <thead>
                <tr className="border-b text-xs text-muted-foreground">
                  {columns.map((column) => (
                    <th
                      key={column.key}
                      scope="col"
                      className={cn(
                        "py-2 font-medium",
                        column.align === "right" ? "text-right" : "text-left"
                      )}
                    >
                      {column.header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const clickable = Boolean(onRowClick);
                  return (
                    <tr
                      key={rowKey(row)}
                      className={cn(
                        "border-b last:border-0",
                        clickable &&
                          "cursor-pointer transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-inset motion-reduce:transition-none"
                      )}
                      tabIndex={clickable ? 0 : undefined}
                      role={clickable ? "button" : undefined}
                      onClick={clickable ? () => onRowClick?.(row) : undefined}
                      onKeyDown={
                        clickable
                          ? (event) => {
                              if (event.key === "Enter" || event.key === " ") {
                                event.preventDefault();
                                onRowClick?.(row);
                              }
                            }
                          : undefined
                      }
                    >
                      {columns.map((column) => (
                        <td
                          key={column.key}
                          className={cn("py-2", column.align === "right" ? "text-right" : "text-left")}
                        >
                          {column.render(row)}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
