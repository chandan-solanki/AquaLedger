import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

import { ClearFiltersButton } from "./ClearFiltersButton";
import { FilterChip } from "./FilterChip";

export interface AppliedFilter {
  key: string;
  label: string;
}

export interface AppliedFiltersProps {
  filters: AppliedFilter[];
  onRemove: (key: string) => void;
  onClearAll?: () => void;
  /** Rendered in place of the row when `filters` is empty — omit to render nothing. */
  emptyState?: ReactNode;
  className?: string;
}

/**
 * The row of currently-active filters as removable chips, plus a Clear All
 * — the visible summary of whatever a `FilterPanel`/`AdvancedFilter`
 * currently holds, per `06_COMPONENT_LIBRARY.md` §6. Takes an already-
 * derived `filters` list (key + human label); deriving that label from raw
 * filter values is the owning feature's job, not this component's.
 */
export function AppliedFilters({
  filters,
  onRemove,
  onClearAll,
  emptyState = null,
  className,
}: AppliedFiltersProps) {
  if (filters.length === 0) return <>{emptyState}</>;

  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      {filters.map((filter) => (
        <FilterChip key={filter.key} label={filter.label} onRemove={() => onRemove(filter.key)} />
      ))}
      {onClearAll && <ClearFiltersButton onClear={onClearAll} count={filters.length} />}
    </div>
  );
}
