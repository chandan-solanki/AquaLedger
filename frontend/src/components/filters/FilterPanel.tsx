"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import { Collapsible as CollapsiblePrimitive } from "radix-ui";
import { ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";

export interface FilterPanelProps {
  title?: string;
  /** Uncontrolled initial state when `open`/`onOpenChange` aren't provided. @defaultValue true */
  defaultOpen?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  /** Rendered beside the title, outside the collapsible toggle (e.g. a `FilterBadge` or `ClearFiltersButton`). */
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

/**
 * The collapsible container every List page's filter UI lives inside, per
 * `06_COMPONENT_LIBRARY.md` §6 Filter Panel. Genuinely generic — it has no
 * idea what its `children` are; a page fills it with `FilterSection`/
 * `FilterGroup`/any typed filter control below. Built on Radix Collapsible
 * for correct keyboard toggling (`Enter`/`Space` on the trigger) and
 * `aria-expanded` wiring, rather than a hand-rolled show/hide `useState`.
 */
export function FilterPanel({
  title = "Filters",
  defaultOpen = true,
  open,
  onOpenChange,
  actions,
  children,
  className,
}: FilterPanelProps) {
  const [uncontrolledOpen, setUncontrolledOpen] = useState(defaultOpen);
  const isControlled = open !== undefined;
  const isOpen = isControlled ? open : uncontrolledOpen;

  function handleOpenChange(next: boolean) {
    if (!isControlled) setUncontrolledOpen(next);
    onOpenChange?.(next);
  }

  return (
    <CollapsiblePrimitive.Root
      open={isOpen}
      onOpenChange={handleOpenChange}
      className={cn("rounded-lg border", className)}
    >
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5">
        <CollapsiblePrimitive.Trigger asChild>
          <button
            type="button"
            className="flex items-center gap-1.5 rounded-md text-sm font-medium outline-none hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50"
          >
            <ChevronDown
              className={cn("size-4 text-muted-foreground transition-transform", !isOpen && "-rotate-90")}
              aria-hidden
            />
            {title}
          </button>
        </CollapsiblePrimitive.Trigger>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>

      <CollapsiblePrimitive.Content className="overflow-hidden data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:animate-in data-[state=open]:fade-in-0">
        <div className="flex flex-col gap-4 border-t px-4 py-4">{children}</div>
      </CollapsiblePrimitive.Content>
    </CollapsiblePrimitive.Root>
  );
}
