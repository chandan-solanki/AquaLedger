"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import type { FormEvent } from "react";

import { IconActionButton } from "@/components/layout/action-buttons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const DEFAULT_PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

export interface DataTablePaginationProps {
  /** Zero-based, matching TanStack's own `pageIndex` convention. */
  pageIndex: number;
  pageSize: number;
  totalCount: number;
  onPageChange: (pageIndex: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
  pageSizeOptions?: number[];
  /** When > 0, replaces the "Showing x–y of n" text with a selection count, matching `DataTableToolbar`'s Bulk Actions takeover. */
  selectedCount?: number;
  showPageSizeSelector?: boolean;
  showJumpToPage?: boolean;
  className?: string;
}

/**
 * The paged-results footer, per `06_COMPONENT_LIBRARY.md` §2/§6 Pagination —
 * First/Previous/Next/Last, rows-per-page, jump-to-page, and a total-count
 * display ("Showing 1–50 of 240"), per `02_DESIGN_SYSTEM.md` §9. Consumes
 * pagination state entirely through props and callbacks; it never fetches
 * data itself — the owning feature's TanStack Query hook re-fetches when
 * `onPageChange`/`onPageSizeChange` fire, per `07_FRONTEND_ARCHITECTURE.md`
 * §8's shared pagination contract.
 */
export function DataTablePagination({
  pageIndex,
  pageSize,
  totalCount,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = DEFAULT_PAGE_SIZE_OPTIONS,
  selectedCount = 0,
  showPageSizeSelector = true,
  showJumpToPage = true,
  className,
}: DataTablePaginationProps) {
  const pageCount = Math.max(1, Math.ceil(totalCount / pageSize));
  const currentPage = pageIndex + 1;
  const canPrevious = pageIndex > 0;
  const canNext = pageIndex < pageCount - 1;
  const from = totalCount === 0 ? 0 : pageIndex * pageSize + 1;
  const to = Math.min(totalCount, (pageIndex + 1) * pageSize);

  const [jumpValue, setJumpValue] = useState("");

  function handleJump(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const target = Number(jumpValue);
    if (Number.isFinite(target) && target >= 1 && target <= pageCount) {
      onPageChange(target - 1);
    }
    setJumpValue("");
  }

  return (
    <div
      className={cn(
        "flex flex-wrap items-center justify-between gap-4 px-1 py-1",
        className
      )}
    >
      <p className="text-sm text-muted-foreground" role="status">
        {selectedCount > 0
          ? `${selectedCount} of ${totalCount} row(s) selected`
          : totalCount === 0
            ? "No results"
            : `Showing ${from}–${to} of ${totalCount}`}
      </p>

      <div className="flex flex-wrap items-center gap-4">
        {showPageSizeSelector && onPageSizeChange && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground whitespace-nowrap">Rows per page</span>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className="flex h-8 items-center gap-1 rounded-md border bg-background px-2.5 text-sm shadow-xs outline-none hover:bg-accent hover:text-accent-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50"
                  aria-label="Rows per page"
                >
                  {pageSize}
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {pageSizeOptions.map((size) => (
                  <DropdownMenuItem key={size} onClick={() => onPageSizeChange(size)}>
                    {size}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}

        <p className="text-sm text-muted-foreground whitespace-nowrap" aria-live="polite">
          Page {currentPage} of {pageCount}
        </p>

        {showJumpToPage && pageCount > 1 && (
          <form onSubmit={handleJump} className="flex items-center gap-1.5">
            <label
              htmlFor="data-table-jump-to-page"
              className="text-sm text-muted-foreground whitespace-nowrap"
            >
              Go to
            </label>
            <Input
              id="data-table-jump-to-page"
              type="number"
              min={1}
              max={pageCount}
              value={jumpValue}
              onChange={(event) => setJumpValue(event.target.value)}
              className="h-8 w-16 px-2"
              aria-label="Jump to page"
            />
          </form>
        )}

        <div className="flex items-center gap-1">
          <IconActionButton
            icon={ChevronsLeft}
            label="First page"
            disabled={!canPrevious}
            onClick={() => onPageChange(0)}
          />
          <IconActionButton
            icon={ChevronLeft}
            label="Previous page"
            disabled={!canPrevious}
            onClick={() => onPageChange(pageIndex - 1)}
          />
          <IconActionButton
            icon={ChevronRight}
            label="Next page"
            disabled={!canNext}
            onClick={() => onPageChange(pageIndex + 1)}
          />
          <IconActionButton
            icon={ChevronsRight}
            label="Last page"
            disabled={!canNext}
            onClick={() => onPageChange(pageCount - 1)}
          />
        </div>
      </div>
    </div>
  );
}
