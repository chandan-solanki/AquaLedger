"use client";

import { X } from "lucide-react";

import { NumberInput } from "@/components/form/NumberInput";
import { IconActionButton } from "@/components/layout/action-buttons";
import { cn } from "@/lib/utils";

export interface NumberRangeValue {
  min?: string;
  max?: string;
}

export interface NumberRangeFilterProps {
  label?: string;
  value: NumberRangeValue;
  onChange: (value: NumberRangeValue) => void;
  minPlaceholder?: string;
  maxPlaceholder?: string;
  decimalPlaces?: number;
  onClear?: () => void;
  className?: string;
}

/**
 * A min/max numeric range filter — reuses `components/form`'s `NumberInput`
 * for both bounds (same character/decimal-place sanitization every other
 * numeric field in the product gets) rather than a bespoke pair of raw
 * `<input>`s.
 */
export function NumberRangeFilter({
  label,
  value,
  onChange,
  minPlaceholder = "Min",
  maxPlaceholder = "Max",
  decimalPlaces = 0,
  onClear,
  className,
}: NumberRangeFilterProps) {
  const hasValue = Boolean(value.min || value.max);

  return (
    <div className={cn("space-y-2", className)}>
      {label && <span className="text-sm font-medium">{label}</span>}
      <div className="flex items-center gap-2">
        <NumberInput
          aria-label={minPlaceholder}
          placeholder={minPlaceholder}
          decimalPlaces={decimalPlaces}
          value={value.min ?? ""}
          onChange={(event) => onChange({ ...value, min: event.target.value })}
        />
        <span className="text-sm text-muted-foreground">to</span>
        <NumberInput
          aria-label={maxPlaceholder}
          placeholder={maxPlaceholder}
          decimalPlaces={decimalPlaces}
          value={value.max ?? ""}
          onChange={(event) => onChange({ ...value, max: event.target.value })}
        />
        {onClear && hasValue && <IconActionButton icon={X} label="Clear range" onClick={onClear} />}
      </div>
    </div>
  );
}
