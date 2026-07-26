"use client";

import { X } from "lucide-react";

import { Button } from "@/components/ui/button";

export interface ClearFiltersButtonProps {
  onClear: () => void;
  /** When provided, shown as "Clear (N)" and the button disables itself at `0`. */
  count?: number;
  disabled?: boolean;
  className?: string;
}

/**
 * A single, consistent "reset everything" action for a filter UI — used
 * identically inside `AppliedFilters`, a `FilterPanel`'s header actions, or
 * an `AdvancedFilter`'s footer.
 */
export function ClearFiltersButton({ onClear, count, disabled, className }: ClearFiltersButtonProps) {
  const isDisabled = disabled ?? count === 0;

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      onClick={onClear}
      disabled={isDisabled}
      className={className}
    >
      <X aria-hidden />
      {count !== undefined && count > 0 ? `Clear (${count})` : "Clear filters"}
    </Button>
  );
}
