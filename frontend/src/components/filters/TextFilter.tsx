"use client";

import { useId } from "react";
import { X } from "lucide-react";

import { IconActionButton } from "@/components/layout/action-buttons";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export interface TextFilterProps {
  label?: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  id?: string;
  className?: string;
}

/**
 * A single free-text, field-scoped filter (e.g. "Reference contains…") —
 * the `FilterPanel`/`AdvancedFilter`-context sibling of the Toolbar-level
 * `SearchBar`. Applies immediately on change; debouncing it, if a feature
 * wants that, is the same `useSearch` hook `SearchBar` uses.
 */
export function TextFilter({ label, value, onChange, placeholder, id, className }: TextFilterProps) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;

  return (
    <div className={cn("space-y-1.5", className)}>
      {label && <Label htmlFor={fieldId}>{label}</Label>}
      <div className="relative">
        <Input
          id={fieldId}
          value={value}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
          className="pr-8"
        />
        {value && (
          <div className="absolute top-1/2 right-1 -translate-y-1/2">
            <IconActionButton icon={X} label="Clear" size="icon-sm" onClick={() => onChange("")} />
          </div>
        )}
      </div>
    </div>
  );
}
