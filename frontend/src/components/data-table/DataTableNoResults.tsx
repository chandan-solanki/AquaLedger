"use client";

import { SearchX } from "lucide-react";

import { EmptyState } from "@/components/feedback/empty-state";
import { Button } from "@/components/ui/button";

export interface DataTableNoResultsProps {
  title?: string;
  description?: string;
  onClearFilters?: () => void;
  className?: string;
}

/**
 * "No matches for the current search/filter" — distinct from
 * `DataTableEmpty`'s "genuinely no data" state, per `04_USER_FLOWS.md` §21.
 * Offers a clear-filters action instead of a "+ New {Entity}" CTA, since the
 * data the user wants may well exist outside the current filter.
 */
export function DataTableNoResults({
  title = "No results found",
  description = "Try adjusting your search or filters.",
  onClearFilters,
  className,
}: DataTableNoResultsProps) {
  return (
    <EmptyState
      icon={SearchX}
      title={title}
      description={description}
      className={className}
      action={
        onClearFilters && (
          <Button variant="outline" size="sm" onClick={onClearFilters}>
            Clear filters
          </Button>
        )
      }
    />
  );
}
