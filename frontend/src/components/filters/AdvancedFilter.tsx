"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import { SlidersHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

import { FilterBadge } from "./FilterBadge";

export interface AdvancedFilterProps {
  triggerLabel?: string;
  /** Shown as a `FilterBadge` on the trigger — how many of the filters inside currently differ from their defaults. */
  activeCount?: number;
  /** One or more `FilterSection`/`FilterGroup` blocks — this component has no opinion on what filters it holds. */
  children: ReactNode;
  onApply?: () => void;
  onReset?: () => void;
  applyLabel?: string;
  resetLabel?: string;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  className?: string;
  contentClassName?: string;
}

/**
 * The reusable "Advanced Filters" container — a Popover trigger (with an
 * active-filter-count badge) opening a panel that holds however many
 * `FilterSection`/`FilterGroup` blocks the consuming List page needs, per
 * `06_COMPONENT_LIBRARY.md` §6/§10 Advanced Filter Builder's "structured
 * multi-condition filter constructor" role. `onApply`/`onReset` are
 * optional — omit both for filters that should take effect immediately as
 * they're changed, matching `02_DESIGN_SYSTEM.md` §8's Switch-vs-explicit-
 * Save distinction applied to filters.
 */
export function AdvancedFilter({
  triggerLabel = "Advanced Filters",
  activeCount = 0,
  children,
  onApply,
  onReset,
  applyLabel = "Apply",
  resetLabel = "Reset",
  open,
  onOpenChange,
  className,
  contentClassName,
}: AdvancedFilterProps) {
  const [uncontrolledOpen, setUncontrolledOpen] = useState(false);
  const isControlled = open !== undefined;
  const isOpen = isControlled ? open : uncontrolledOpen;

  function handleOpenChange(next: boolean) {
    if (!isControlled) setUncontrolledOpen(next);
    onOpenChange?.(next);
  }

  return (
    <Popover open={isOpen} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>
        <Button type="button" variant="outline" size="sm" className={cn("gap-2", className)}>
          <SlidersHorizontal />
          {triggerLabel}
          <FilterBadge count={activeCount} />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className={cn("w-80 p-4", contentClassName)}>
        <div className="flex flex-col gap-4">
          {children}

          {(onApply || onReset) && (
            <div className="flex items-center justify-between border-t pt-3">
              {onReset ? (
                <Button type="button" variant="ghost" size="sm" onClick={onReset}>
                  {resetLabel}
                </Button>
              ) : (
                <span />
              )}
              {onApply && (
                <Button
                  type="button"
                  size="sm"
                  onClick={() => {
                    onApply();
                    handleOpenChange(false);
                  }}
                >
                  {applyLabel}
                </Button>
              )}
            </div>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
