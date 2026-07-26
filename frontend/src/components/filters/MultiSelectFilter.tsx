"use client";

import { useState } from "react";
import { Check, ChevronsUpDown } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

import { FilterChip } from "./FilterChip";

export interface MultiSelectOption<TValue extends string = string> {
  value: TValue;
  label: string;
}

export interface MultiSelectFilterProps<TValue extends string = string> {
  label?: string;
  options: MultiSelectOption<TValue>[];
  value: TValue[];
  onChange: (value: TValue[]) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  emptyMessage?: string;
  className?: string;
}

/**
 * A searchable multi-select filter, per `02_DESIGN_SYSTEM.md` §4 Multi
 * Select's "each choice shown as a removable tag" convention — the same
 * Popover+Command foundation as `components/form`'s `Combobox`, but with a
 * checkbox-style multi-selection model instead of single-select.
 */
export function MultiSelectFilter<TValue extends string = string>({
  label,
  options,
  value,
  onChange,
  placeholder = "Select…",
  searchPlaceholder = "Search…",
  emptyMessage = "No matches found.",
  className,
}: MultiSelectFilterProps<TValue>) {
  const [open, setOpen] = useState(false);
  const selectedOptions = options.filter((option) => value.includes(option.value));

  function toggle(optionValue: TValue) {
    onChange(
      value.includes(optionValue) ? value.filter((v) => v !== optionValue) : [...value, optionValue]
    );
  }

  return (
    <div className={cn("space-y-2", className)}>
      {label && <span className="text-sm font-medium">{label}</span>}
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className={cn(
              "w-full justify-between font-normal",
              selectedOptions.length === 0 && "text-muted-foreground"
            )}
          >
            <span className="truncate">
              {selectedOptions.length > 0 ? `${selectedOptions.length} selected` : placeholder}
            </span>
            <ChevronsUpDown className="ml-2 size-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent align="start" className="p-0">
          <Command>
            <CommandInput placeholder={searchPlaceholder} />
            <CommandList>
              <CommandEmpty>{emptyMessage}</CommandEmpty>
              <CommandGroup>
                {options.map((option) => {
                  const selected = value.includes(option.value);
                  return (
                    <CommandItem
                      key={option.value}
                      value={option.label}
                      onSelect={() => toggle(option.value)}
                    >
                      <Check className={cn("size-4", selected ? "opacity-100" : "opacity-0")} aria-hidden />
                      {option.label}
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {selectedOptions.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selectedOptions.map((option) => (
            <FilterChip key={option.value} label={option.label} onRemove={() => toggle(option.value)} />
          ))}
        </div>
      )}
    </div>
  );
}
