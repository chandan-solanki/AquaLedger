"use client";

import { useState } from "react";
import type { ComponentProps } from "react";
import { format } from "date-fns";
import { CalendarIcon, X } from "lucide-react";
import type { DateRange } from "react-day-picker";

import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { DEFAULT_DATE_FORMAT } from "@/lib/date-format";
import { cn } from "@/lib/utils";

import { FormField } from "./FormField";

export interface DateRangePickerProps {
  label?: string;
  description?: string;
  error?: string;
  required?: boolean;
  disabled?: boolean;
  placeholder?: string;
  value?: DateRange;
  onChange?: (range: DateRange | undefined) => void;
  dateFormat?: string;
  disabledDates?: ComponentProps<typeof Calendar>["disabled"];
  numberOfMonths?: number;
  id?: string;
  containerClassName?: string;
  className?: string;
}

/**
 * The two-ended Date Picker variant for filter bars (Reports, List page date
 * filters), per `06_COMPONENT_LIBRARY.md` §4 — Start/End selected together
 * in one range-mode calendar, plus an explicit Clear action rather than
 * requiring the user to reopen the popover and deselect each bound.
 */
export function DateRangePicker({
  label,
  description,
  error,
  required,
  disabled,
  placeholder,
  value,
  onChange,
  dateFormat = DEFAULT_DATE_FORMAT,
  disabledDates,
  numberOfMonths = 2,
  id,
  containerClassName,
  className,
}: DateRangePickerProps) {
  const [open, setOpen] = useState(false);

  const displayText = value?.from
    ? value.to
      ? `${format(value.from, dateFormat)} – ${format(value.to, dateFormat)}`
      : format(value.from, dateFormat)
    : "";

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
              disabled={disabled}
              aria-invalid={ariaInvalid}
              aria-describedby={describedBy}
              aria-required={required}
              className={cn(
                "w-full justify-start gap-2 font-normal",
                !displayText && "text-muted-foreground",
                className
              )}
            >
              <CalendarIcon className="size-4" />
              {displayText || placeholder || "Select a date range"}
            </Button>
          </PopoverTrigger>
          <PopoverContent align="start" className="w-auto p-0">
            <Calendar
              mode="range"
              selected={value}
              defaultMonth={value?.from}
              numberOfMonths={numberOfMonths}
              disabled={disabledDates}
              onSelect={onChange}
            />
            <div className="flex justify-end border-t p-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  onChange?.(undefined);
                  setOpen(false);
                }}
              >
                <X />
                Clear
              </Button>
            </div>
          </PopoverContent>
        </Popover>
      )}
    </FormField>
  );
}
