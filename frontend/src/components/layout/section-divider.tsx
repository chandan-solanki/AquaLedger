import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

interface SectionDividerProps {
  label?: string;
  className?: string;
}

/**
 * A horizontal rule dividing page/form sections, with an optional inline
 * label (e.g. "Advanced"). A documented composition of the existing
 * Separator primitive, per `06_COMPONENT_LIBRARY.md` §19's rule against
 * introducing a new component where a variant of an existing one suffices.
 */
export function SectionDivider({ label, className }: SectionDividerProps) {
  if (!label) {
    return <Separator className={className} />;
  }

  return (
    <div className={cn("flex items-center gap-3", className)} role="separator">
      <Separator className="flex-1" />
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <Separator className="flex-1" />
    </div>
  );
}
