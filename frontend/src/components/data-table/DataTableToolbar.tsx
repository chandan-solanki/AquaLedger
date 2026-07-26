import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface DataTableToolbarProps {
  /** Typically a Search Input (`06_COMPONENT_LIBRARY.md` §4), scoped and labeled per the table's own documented searchable fields. */
  search?: ReactNode;
  /** The Filter Panel/Quick Filters row for this table's module-specific filter set. */
  filters?: ReactNode;
  /** `DataTableColumnToggle`, or any other view-configuration control. */
  viewOptions?: ReactNode;
  exportSlot?: ReactNode;
  refresh?: ReactNode;
  /** Rendered in place of every other slot once `selectedCount > 0`, per `06_COMPONENT_LIBRARY.md` §6 Bulk Actions. */
  bulkActions?: ReactNode;
  selectedCount?: number;
  className?: string;
}

/**
 * The row directly above the Data Table (`06_COMPONENT_LIBRARY.md` §6
 * Toolbar) — purely slot-driven, nothing hardcoded. A feature composes
 * exactly the controls its module needs (a Search Input, a Filter Panel, an
 * Export button, `DataTableColumnToggle`) without this component knowing
 * what any of them are or how they work. Renders unconditionally even if
 * every slot is empty, so it's safe to always render for layout consistency
 * across List pages — an empty toolbar just renders as empty space.
 */
export function DataTableToolbar({
  search,
  filters,
  viewOptions,
  exportSlot,
  refresh,
  bulkActions,
  selectedCount = 0,
  className,
}: DataTableToolbarProps) {
  if (selectedCount > 0 && bulkActions) {
    return (
      <div
        className={cn(
          "flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/40 px-3 py-2",
          className
        )}
      >
        <p className="text-sm font-medium">{selectedCount} selected</p>
        <div className="flex flex-wrap items-center gap-2">{bulkActions}</div>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-wrap items-center justify-between gap-3", className)}>
      <div className="flex flex-1 flex-wrap items-center gap-2">
        {search}
        {filters}
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        {refresh}
        {exportSlot}
        {viewOptions}
      </div>
    </div>
  );
}
