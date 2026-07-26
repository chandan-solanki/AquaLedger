"use client";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const DEFAULT_OPTIONS = [10, 25, 50, 100];

export interface PageSizeSelectorProps {
  pageSize: number;
  onPageSizeChange: (pageSize: number) => void;
  options?: number[];
  label?: string;
  disabled?: boolean;
  className?: string;
}

/**
 * The rows-per-page control, per `02_DESIGN_SYSTEM.md` §9 — configurable
 * option set, purely props-driven.
 */
export function PageSizeSelector({
  pageSize,
  onPageSizeChange,
  options = DEFAULT_OPTIONS,
  label = "Rows per page",
  disabled = false,
  className,
}: PageSizeSelectorProps) {
  return (
    <div className={className}>
      {label && (
        <span id="page-size-label" className="mr-2 text-sm whitespace-nowrap text-muted-foreground">
          {label}
        </span>
      )}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            disabled={disabled}
            aria-labelledby={label ? "page-size-label" : undefined}
            aria-label={label ? undefined : "Rows per page"}
            className="inline-flex h-8 items-center gap-1 rounded-md border bg-background px-2.5 text-sm shadow-xs outline-none hover:bg-accent hover:text-accent-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {pageSize}
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {options.map((option) => (
            <DropdownMenuItem key={option} onClick={() => onPageSizeChange(option)}>
              {option}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
