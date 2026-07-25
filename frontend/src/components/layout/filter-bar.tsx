"use client";

import type { ReactNode } from "react";
import { Calendar, ChevronDown, Search, X } from "lucide-react";

import { ToolbarButton } from "@/components/layout/action-buttons";
import { Input } from "@/components/ui/input";
import { toastInfo } from "@/lib/toast";

interface FilterBarProps {
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  /** Shown when a Date Range field is relevant for this module — not a real Date Range Picker yet (that's Sprint 2 Component Library scope). */
  showDateRange?: boolean;
  /** Shown when a Status field is relevant for this module — not a real Select yet, same reason as `showDateRange`. */
  showStatus?: boolean;
  statusLabel?: string;
  onReset?: () => void;
  /** Extra module-specific filter controls, appended after the fixed set. */
  children?: ReactNode;
  className?: string;
}

/**
 * The structured-filter portion of a List page's Toolbar, per
 * `06_COMPONENT_LIBRARY.md` §6 (Filter Panel) — free-text search plus the
 * small set of most-relevant structured filters, never hidden behind an
 * extra click. `showDateRange`/`showStatus` render inert placeholder
 * triggers (consistent with the Search/Notifications placeholders already
 * in `AppHeader`) until the real Date Range Picker / Select primitives
 * exist — a business module swaps them for working controls without
 * changing this component's layout.
 */
export function FilterBar({
  searchValue,
  onSearchChange,
  searchPlaceholder = "Search…",
  showDateRange = false,
  showStatus = false,
  statusLabel = "Status",
  onReset,
  children,
  className,
}: FilterBarProps) {
  return (
    <div className={className}>
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-50 flex-1 sm:max-w-xs">
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

        {showDateRange && (
          <ToolbarButton onClick={() => toastInfo("Date range filtering is coming soon.")}>
            <Calendar />
            Date Range
          </ToolbarButton>
        )}

        {showStatus && (
          <ToolbarButton onClick={() => toastInfo("Status filtering is coming soon.")}>
            {statusLabel}
            <ChevronDown className="size-3.5" aria-hidden />
          </ToolbarButton>
        )}

        {children}

        {onReset && (
          <ToolbarButton onClick={onReset}>
            <X />
            Reset
          </ToolbarButton>
        )}
      </div>
    </div>
  );
}
