import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export interface DataTableLoadingProps {
  columnCount?: number;
  rowCount?: number;
  className?: string;
}

/**
 * The Data Table's Loading State — skeleton rows matching the real table's
 * column count, per `06_COMPONENT_LIBRARY.md` §12 Table Skeleton. Rendered
 * inside the table body (a single full-width cell spanning every column) so
 * the header — and any sticky/pinned columns — stay visible while data
 * resolves. Shows immediately with no minimum display duration, per
 * `02_DESIGN_SYSTEM.md` §14.
 */
export function DataTableLoading({ columnCount = 5, rowCount = 8, className }: DataTableLoadingProps) {
  return (
    <div className={cn("w-full", className)} aria-hidden>
      {Array.from({ length: rowCount }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex items-center gap-4 px-4 py-3">
          {Array.from({ length: columnCount }).map((_, colIndex) => (
            <Skeleton key={colIndex} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}
