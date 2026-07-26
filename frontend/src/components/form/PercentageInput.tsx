"use client";

import type { ChangeEvent } from "react";

import { NumberInput, type NumberInputProps } from "./NumberInput";

export type PercentageInputProps = Omit<NumberInputProps, "decimalPlaces" | "suffix" | "allowNegative">;

/**
 * A Number Input variant constrained to 0–100 with a trailing `%` affix, per
 * `06_COMPONENT_LIBRARY.md` §4 — discount/tax rate fields on Invoice/Purchase
 * Bill lines. Clamps to 100 as the user types past it rather than only
 * validating on submit, since letting the field visibly hold an impossible
 * value (e.g. "150") even briefly would contradict the "numbers are never
 * ambiguous" principle in `02_DESIGN_SYSTEM.md` §1.
 */
export function PercentageInput({ onChange, ...props }: PercentageInputProps) {
  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const numeric = Number(event.target.value);
    if (event.target.value !== "" && Number.isFinite(numeric) && numeric > 100) {
      event.target.value = "100";
    }
    onChange?.(event);
  }

  return (
    <NumberInput
      decimalPlaces={2}
      suffix="%"
      inputMode="decimal"
      onChange={handleChange}
      {...props}
    />
  );
}
