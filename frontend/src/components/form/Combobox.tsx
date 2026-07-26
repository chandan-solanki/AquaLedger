"use client";

import { useState } from "react";
import { Check, ChevronsUpDown, Loader2 } from "lucide-react";

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

import { FormField } from "./FormField";

export interface ComboboxOption<TValue extends string = string> {
  value: TValue;
  label: string;
  description?: string;
  disabled?: boolean;
}

export interface ComboboxProps<TValue extends string = string> {
  label?: string;
  description?: string;
  error?: string;
  required?: boolean;
  disabled?: boolean;
  placeholder?: string;
  searchPlaceholder?: string;
  emptyMessage?: string;
  options: ComboboxOption<TValue>[];
  value?: TValue;
  onChange?: (value: TValue | undefined) => void;
  /** Fires on every search-box keystroke. Omit for pure client-side filtering (cmdk's own built-in match against each option's label). */
  onSearchChange?: (query: string) => void;
  isLoading?: boolean;
  /** Disables cmdk's client-side filtering — set this to `false` when `onSearchChange` already narrows `options` server-side, so the two filters don't fight each other. */
  shouldFilter?: boolean;
  id?: string;
  containerClassName?: string;
  className?: string;
}

/**
 * Type-to-filter single-select showing the selected value once chosen, per
 * `06_COMPONENT_LIBRARY.md` §4 — the base Combobox every cross-entity
 * Entity Selector (Fish, Company, Supplier — `06_COMPONENT_LIBRARY.md` §10)
 * will configure from Sprint 4 onward. `SearchableSelect` and `AsyncSelect`
 * are the two fixed configurations of this one component (client-filtered
 * vs. server-filtered), per the reuse rule in `06_COMPONENT_LIBRARY.md` §19
 * — this file owns the only real Popover/Command/keyboard-accessibility
 * implementation.
 */
export function Combobox<TValue extends string = string>({
  label,
  description,
  error,
  required,
  disabled,
  placeholder = "Select…",
  searchPlaceholder = "Search…",
  emptyMessage = "No matches found.",
  options,
  value,
  onChange,
  onSearchChange,
  isLoading = false,
  shouldFilter = true,
  id,
  containerClassName,
  className,
}: ComboboxProps<TValue>) {
  const [open, setOpen] = useState(false);
  const selected = options.find((option) => option.value === value);

  return (
    <FormField
      label={label}
      description={description}
      error={error}
      required={required}
      disabled={disabled}
      id={id}
      className={containerClassName}
    >
      {({ id: fieldId, describedBy, "aria-invalid": ariaInvalid }) => (
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <Button
              id={fieldId}
              type="button"
              variant="outline"
              role="combobox"
              aria-expanded={open}
              aria-invalid={ariaInvalid}
              aria-describedby={describedBy}
              aria-required={required}
              disabled={disabled}
              className={cn(
                "w-full justify-between font-normal",
                !selected && "text-muted-foreground",
                className
              )}
            >
              <span className="truncate">{selected?.label ?? placeholder}</span>
              <ChevronsUpDown className="ml-2 size-4 shrink-0 opacity-50" />
            </Button>
          </PopoverTrigger>
          <PopoverContent align="start" className="p-0">
            <Command shouldFilter={shouldFilter}>
              <CommandInput placeholder={searchPlaceholder} onValueChange={onSearchChange} />
              <CommandList>
                {isLoading ? (
                  <div className="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
                    <Loader2 className="size-4 animate-spin motion-reduce:animate-none" aria-hidden />
                    Loading…
                  </div>
                ) : (
                  <>
                    <CommandEmpty>{emptyMessage}</CommandEmpty>
                    <CommandGroup>
                      {options.map((option) => (
                        <CommandItem
                          key={option.value}
                          value={option.label}
                          disabled={option.disabled}
                          onSelect={() => {
                            onChange?.(option.value === value ? undefined : option.value);
                            setOpen(false);
                          }}
                        >
                          <Check
                            className={cn(
                              "size-4",
                              option.value === value ? "opacity-100" : "opacity-0"
                            )}
                            aria-hidden
                          />
                          <div className="flex flex-col">
                            <span>{option.label}</span>
                            {option.description && (
                              <span className="text-xs text-muted-foreground">
                                {option.description}
                              </span>
                            )}
                          </div>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </>
                )}
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>
      )}
    </FormField>
  );
}
