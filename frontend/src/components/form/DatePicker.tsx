"use client";

import { useEffect, useState } from "react";
import type { ComponentProps } from "react";
import { format, isValid, parse } from "date-fns";
import { CalendarIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { DEFAULT_DATE_FORMAT } from "@/lib/date-format";
import { cn } from "@/lib/utils";

import { FormField } from "./FormField";

export interface DatePickerProps {
  label?: string;
  description?: string;
  error?: string;
  required?: boolean;
  disabled?: boolean;
  placeholder?: string;
  value?: Date;
  onChange?: (date: Date | undefined) => void;
  onBlur?: () => void;
  /** A date-fns format string for both display and typed entry. */
  dateFormat?: string;
  /** Passed straight through to the Calendar's own `disabled` matcher (e.g. `{ before: new Date() }`). */
  disabledDates?: ComponentProps<typeof Calendar>["disabled"];
  name?: string;
  id?: string;
  containerClassName?: string;
  className?: string;
}

/**
 * Calendar popover plus direct typed-date entry, per `06_COMPONENT_LIBRARY.md`
 * §4 — Invoice Date, Due Date, Trip dates. Typing is fully supported without
 * opening the calendar (data-entry speed matters more than clicking through
 * a calendar for this user base); the calendar button is there for the
 * pick-a-date-visually path. A value only commits via `onChange` once it
 * parses to a real date or the field is cleared — a partial/invalid keystroke
 * never silently overwrites the last valid committed value.
 */
export function DatePicker({
  label,
  description,
  error,
  required,
  disabled,
  placeholder,
  value,
  onChange,
  onBlur,
  dateFormat = DEFAULT_DATE_FORMAT,
  disabledDates,
  name,
  id,
  containerClassName,
  className,
}: DatePickerProps) {
  const [open, setOpen] = useState(false);
  const [textValue, setTextValue] = useState(() => (value ? format(value, dateFormat) : ""));

  useEffect(() => {
    setTextValue(value ? format(value, dateFormat) : "");
  }, [value, dateFormat]);

  function commitText(raw: string) {
    setTextValue(raw);
    if (raw.trim() === "") {
      onChange?.(undefined);
      return;
    }
    const parsed = parse(raw, dateFormat, new Date());
    if (isValid(parsed)) {
      onChange?.(parsed);
    }
  }

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
        <div className="relative">
          <Input
            id={fieldId}
            name={name}
            value={textValue}
            placeholder={placeholder ?? dateFormat.toUpperCase()}
            disabled={disabled}
            aria-invalid={ariaInvalid}
            aria-describedby={describedBy}
            aria-required={required}
            onChange={(event) => commitText(event.target.value)}
            onBlur={onBlur}
            className={cn("pr-9", className)}
          />
          <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                disabled={disabled}
                aria-label="Open calendar"
                className="absolute top-1/2 right-1 -translate-y-1/2 text-muted-foreground"
              >
                <CalendarIcon />
              </Button>
            </PopoverTrigger>
            <PopoverContent align="start" className="w-auto p-0">
              <Calendar
                mode="single"
                selected={value}
                defaultMonth={value}
                disabled={disabledDates}
                onSelect={(date) => {
                  onChange?.(date);
                  setOpen(false);
                }}
              />
            </PopoverContent>
          </Popover>
        </div>
      )}
    </FormField>
  );
}
