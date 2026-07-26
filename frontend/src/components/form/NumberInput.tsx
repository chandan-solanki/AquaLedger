"use client";

import type { ChangeEvent, ComponentProps } from "react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

import { FormField } from "./FormField";

export interface NumberInputProps
  extends Omit<ComponentProps<"input">, "type" | "value" | "defaultValue"> {
  label?: string;
  description?: string;
  error?: string;
  required?: boolean;
  /** Digits allowed after the decimal point. `0` restricts entry to whole numbers. */
  decimalPlaces?: number;
  allowNegative?: boolean;
  /** A fixed leading affix (e.g. a currency symbol) — display only, never part of the field's value. */
  prefix?: string;
  /** A fixed trailing affix (e.g. `%`, a unit) — display only, never part of the field's value. */
  suffix?: string;
  value?: string;
  defaultValue?: string;
  /** className for the outer `FormField` wrapper — `className` itself targets the `<input>`. */
  containerClassName?: string;
}

/**
 * Strips a raw keystroke string down to a valid numeric string: only digits,
 * at most one leading `-` (when `allowNegative`), and at most one `.`,
 * truncated to `decimalPlaces` digits after it. Exported so
 * `CurrencyInput`/`QuantityInput`/`RateInput`/`PercentageInput` (and any
 * future numeric variant) can reuse the exact same rule rather than each
 * reimplementing it slightly differently.
 */
export function sanitizeNumericString(
  raw: string,
  decimalPlaces: number,
  allowNegative: boolean
): string {
  let value = raw.replace(allowNegative ? /[^0-9.-]/g : /[^0-9.]/g, "");

  if (allowNegative) {
    const isNegative = value.startsWith("-");
    value = value.replace(/-/g, "");
    if (isNegative) value = `-${value}`;
  }

  const firstDot = value.indexOf(".");
  if (firstDot !== -1) {
    value = value.slice(0, firstDot + 1) + value.slice(firstDot + 1).replace(/\./g, "");
  }

  if (decimalPlaces <= 0) {
    return value.split(".")[0] ?? "";
  }

  const [integerPart, decimalPart] = value.split(".");
  return decimalPart === undefined
    ? integerPart
    : `${integerPart}.${decimalPart.slice(0, decimalPlaces)}`;
}

/**
 * The base Number Input — numeric-only entry with right-aligned, tabular-
 * numeral display, per `06_COMPONENT_LIBRARY.md` §4. `CurrencyInput`,
 * `QuantityInput`, `RateInput`, and `PercentageInput` are all fixed-
 * precision *configurations* of this one component, never separate
 * implementations, per the reuse-over-duplication rule in §19.
 *
 * Invalid characters/excess decimal places are rejected at input time by
 * rewriting `event.target.value` before forwarding the (still-native)
 * change event — this keeps the component a plain, DOM-`ref`-forwarding
 * `<input>` from React Hook Form's point of view, so both `register()` and
 * `Controller` work exactly as they would with any other text input.
 */
export function NumberInput({
  label,
  description,
  error,
  required,
  disabled,
  readOnly,
  decimalPlaces = 0,
  allowNegative = false,
  prefix,
  suffix,
  onChange,
  className,
  containerClassName,
  id,
  ...props
}: NumberInputProps) {
  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const sanitized = sanitizeNumericString(event.target.value, decimalPlaces, allowNegative);
    if (sanitized !== event.target.value) {
      event.target.value = sanitized;
    }
    onChange?.(event);
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
          {prefix && (
            <span className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-sm text-muted-foreground">
              {prefix}
            </span>
          )}
          <Input
            id={fieldId}
            type="text"
            inputMode="decimal"
            disabled={disabled}
            readOnly={readOnly}
            aria-invalid={ariaInvalid}
            aria-describedby={describedBy}
            aria-required={required}
            onChange={handleChange}
            className={cn(
              "text-right tabular-nums",
              prefix && "pl-7",
              suffix && "pr-8",
              className
            )}
            {...props}
          />
          {suffix && (
            <span className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 text-sm text-muted-foreground">
              {suffix}
            </span>
          )}
        </div>
      )}
    </FormField>
  );
}
