"use client";

import type { ReactNode } from "react";
import { Columns3, Download, ListFilter, RefreshCw, Search } from "lucide-react";

import { IconActionButton, ToolbarButton } from "@/components/layout/action-buttons";
import { Input } from "@/components/ui/input";
import { toastInfo } from "@/lib/toast";

interface TableToolbarProps {
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  onFiltersClick?: () => void;
  onRefresh?: () => void;
  /** Placeholder — Column Selector isn't built yet (Sprint 2 Component Library scope). */
  showColumnToggle?: boolean;
  /** Placeholder — Export isn't wired to real data yet. */
  showExport?: boolean;
  /** Rendered in place of the search/filter controls once rows are selected, per `06_COMPONENT_LIBRARY.md` §6 Bulk Actions. */
  selectedCount?: number;
  bulkActions?: ReactNode;
  className?: string;
}

/**
 * The row directly above the (future) Enterprise Data Table, per
 * `06_COMPONENT_LIBRARY.md` §6 — distinct from `PageToolbar`'s page-level
 * concerns (Primary CTA, page search) in that it carries table-density
 * controls (Column Selector, Export, Refresh) and the Bulk Actions
 * takeover. Every List module built in a future session reuses this
 * unchanged rather than hand-rolling its own table header row.
 */
export function TableToolbar({
  searchValue,
  onSearchChange,
  searchPlaceholder = "Search…",
  onFiltersClick,
  onRefresh,
  showColumnToggle = true,
  showExport = true,
  selectedCount = 0,
  bulkActions,
  className,
}: TableToolbarProps) {
  if (selectedCount > 0) {
    return (
      <div className={className}>
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/40 px-3 py-2">
          <p className="text-sm font-medium">{selectedCount} selected</p>
          <div className="flex flex-wrap items-center gap-2">{bulkActions}</div>
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-50">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
            <Input
              type="search"
              placeholder={searchPlaceholder}
              value={searchValue}
              onChange={(event) => onSearchChange?.(event.target.value)}
              className="pl-8"
              aria-label="Search"
            />
          </div>
          <ToolbarButton onClick={onFiltersClick ?? (() => toastInfo("Filters are coming soon."))}>
            <ListFilter />
            Filters
          </ToolbarButton>
        </div>

        <div className="flex flex-wrap items-center gap-1">
          {showColumnToggle && (
            <IconActionButton
              icon={Columns3}
              label="Choose columns"
              onClick={() => toastInfo("Column selection is coming soon.")}
            />
          )}
          {showExport && (
            <IconActionButton
              icon={Download}
              label="Export"
              onClick={() => toastInfo("Export is coming soon.")}
            />
          )}
          <IconActionButton
            icon={RefreshCw}
            label="Refresh"
            onClick={onRefresh ?? (() => toastInfo("Refresh isn't wired to live data yet."))}
          />
        </div>
      </div>
    </div>
  );
}
