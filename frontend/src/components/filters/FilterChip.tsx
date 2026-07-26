"use client";

import { X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export interface FilterChipProps {
  label: string;
  onRemove?: () => void;
  className?: string;
}

/**
 * A single applied filter, shown as a removable pill — per
 * `06_COMPONENT_LIBRARY.md` §4's Multi Select "removable tag" convention,
 * reused here for `AppliedFilters`' row of currently-active filters.
 * Renders as a plain (non-removable) badge when `onRemove` is omitted.
 */
export function FilterChip({ label, onRemove, className }: FilterChipProps) {
  return (
    <Badge variant="secondary" className={cn("gap-1 py-1 pr-1 pl-2.5", className)}>
      <span>{label}</span>
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          aria-label={`Remove ${label} filter`}
          className="rounded-full p-0.5 outline-none hover:bg-background/60 focus-visible:ring-[2px] focus-visible:ring-ring/50"
        >
          <X className="size-3" aria-hidden />
        </button>
      )}
    </Badge>
  );
}
