"use client";

import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, MoreHorizontal } from "lucide-react";

import { IconActionButton } from "@/components/layout/action-buttons";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const ELLIPSIS = "ellipsis" as const;
export type PaginationToken = number | typeof ELLIPSIS;

function range(start: number, end: number): number[] {
  return Array.from({ length: end - start + 1 }, (_, i) => start + i);
}

/**
 * Computes the page-number tokens `Pagination` renders: every page when
 * `totalPages` is small enough to show in full, otherwise the first page,
 * the last page, the pages around `page`, and an `"ellipsis"` token
 * wherever a run of pages is collapsed. Exported standalone so a consumer
 * that needs the raw sequence (without this component's markup) can reuse
 * the exact same logic.
 */
export function getPaginationRange(
  page: number,
  totalPages: number,
  siblingCount = 1
): PaginationToken[] {
  const totalPageNumbers = siblingCount * 2 + 5;

  if (totalPageNumbers >= totalPages) {
    return range(1, totalPages);
  }

  const leftSiblingIndex = Math.max(page - siblingCount, 1);
  const rightSiblingIndex = Math.min(page + siblingCount, totalPages);

  const shouldShowLeftDots = leftSiblingIndex > 2;
  const shouldShowRightDots = rightSiblingIndex < totalPages - 2;

  if (!shouldShowLeftDots && shouldShowRightDots) {
    const leftItemCount = 3 + 2 * siblingCount;
    return [...range(1, leftItemCount), ELLIPSIS, totalPages];
  }

  if (shouldShowLeftDots && !shouldShowRightDots) {
    const rightItemCount = 3 + 2 * siblingCount;
    return [1, ELLIPSIS, ...range(totalPages - rightItemCount + 1, totalPages)];
  }

  return [1, ELLIPSIS, ...range(leftSiblingIndex, rightSiblingIndex), ELLIPSIS, totalPages];
}

export interface PaginationProps {
  /** 1-based current page. */
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  /** Page-number buttons shown on each side of the current page. @defaultValue 1 */
  siblingCount?: number;
  showFirstLast?: boolean;
  disabled?: boolean;
  className?: string;
  "aria-label"?: string;
}

/**
 * The reusable page-number control — First/Previous/[collapsed page
 * numbers]/Next/Last, per `06_COMPONENT_LIBRARY.md` §2/§6 Pagination.
 * Purely props-driven: `onPageChange` is the only way it communicates,
 * never fetching or knowing what it's paginating.
 */
export function Pagination({
  page,
  totalPages,
  onPageChange,
  siblingCount = 1,
  showFirstLast = true,
  disabled = false,
  className,
  "aria-label": ariaLabel = "Pagination",
}: PaginationProps) {
  const tokens = getPaginationRange(page, totalPages, siblingCount);
  const canPrevious = !disabled && page > 1;
  const canNext = !disabled && page < totalPages;

  return (
    <nav aria-label={ariaLabel} className={cn("flex items-center gap-1", className)}>
      {showFirstLast && (
        <IconActionButton
          icon={ChevronsLeft}
          label="First page"
          disabled={!canPrevious}
          onClick={() => onPageChange(1)}
        />
      )}
      <IconActionButton
        icon={ChevronLeft}
        label="Previous page"
        disabled={!canPrevious}
        onClick={() => onPageChange(page - 1)}
      />

      <ul className="flex items-center gap-1" role="list">
        {tokens.map((token, index) =>
          token === ELLIPSIS ? (
            <li key={`ellipsis-${index}`} aria-hidden className="flex size-8 items-center justify-center text-muted-foreground">
              <MoreHorizontal className="size-4" />
            </li>
          ) : (
            <li key={token}>
              <Button
                type="button"
                size="icon-sm"
                variant={token === page ? "default" : "outline"}
                disabled={disabled}
                aria-current={token === page ? "page" : undefined}
                aria-label={`Page ${token}`}
                onClick={() => onPageChange(token)}
              >
                {token}
              </Button>
            </li>
          )
        )}
      </ul>

      <IconActionButton
        icon={ChevronRight}
        label="Next page"
        disabled={!canNext}
        onClick={() => onPageChange(page + 1)}
      />
      {showFirstLast && (
        <IconActionButton
          icon={ChevronsRight}
          label="Last page"
          disabled={!canNext}
          onClick={() => onPageChange(totalPages)}
        />
      )}
    </nav>
  );
}
