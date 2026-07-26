"use client";

import { useId } from "react";

import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

export interface BooleanFilterProps {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  id?: string;
  className?: string;
}

/**
 * A binary filter (e.g. "Show inactive only") — uses `Switch`, not
 * `Checkbox`, since a filter takes effect immediately as it's toggled, per
 * `02_DESIGN_SYSTEM.md` §8's "Switch is for immediate-effect settings,
 * never a field requiring an explicit form Save" rule.
 */
export function BooleanFilter({
  label,
  description,
  checked,
  onChange,
  disabled,
  id,
  className,
}: BooleanFilterProps) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;

  return (
    <div className={cn("flex items-center justify-between gap-3", className)}>
      <div>
        <Label htmlFor={fieldId} className="font-normal">
          {label}
        </Label>
        {description && <p className="text-xs text-muted-foreground">{description}</p>}
      </div>
      <Switch id={fieldId} checked={checked} onCheckedChange={onChange} disabled={disabled} />
    </div>
  );
}
