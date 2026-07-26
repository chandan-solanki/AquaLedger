import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface FilterGroupProps {
  label?: string;
  children: ReactNode;
  /** @defaultValue "vertical" */
  orientation?: "vertical" | "horizontal";
  className?: string;
}

/**
 * A tighter grouping of related filter controls than `FilterSection` (a
 * checkbox/pill cluster, not a whole panel block) — real `<fieldset>`/
 * `<legend>` semantics so assistive technology announces the group's
 * purpose once, not per control, per `06_COMPONENT_LIBRARY.md` §15.
 */
export function FilterGroup({ label, children, orientation = "vertical", className }: FilterGroupProps) {
  return (
    <fieldset className={cn("min-w-0 space-y-2 border-0 p-0", className)}>
      {label && <legend className="mb-1 text-sm font-medium">{label}</legend>}
      <div className={cn("flex gap-2", orientation === "vertical" ? "flex-col" : "flex-wrap items-center")}>
        {children}
      </div>
    </fieldset>
  );
}
