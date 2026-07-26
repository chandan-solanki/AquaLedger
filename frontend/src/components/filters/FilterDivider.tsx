import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

export interface FilterDividerProps {
  /** @defaultValue "horizontal" */
  orientation?: "horizontal" | "vertical";
  className?: string;
}

/**
 * A thin visual divider between filter controls/sections — wraps the
 * existing `Separator` primitive rather than a new implementation, per
 * `06_COMPONENT_LIBRARY.md` §19.
 */
export function FilterDivider({ orientation = "horizontal", className }: FilterDividerProps) {
  return (
    <Separator
      orientation={orientation}
      className={cn(orientation === "vertical" ? "h-6" : "my-1", className)}
    />
  );
}
