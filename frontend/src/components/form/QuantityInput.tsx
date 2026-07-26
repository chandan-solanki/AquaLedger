"use client";

import { NumberInput, type NumberInputProps } from "./NumberInput";

export interface QuantityInputProps extends Omit<NumberInputProps, "decimalPlaces"> {
  /** e.g. "kg" — rendered as a trailing suffix, per the Quantity field's `NUMERIC(12,3)` weight precision. */
  unit?: string;
}

/**
 * A Number Input variant fixed to the backend's weight precision
 * (`NUMERIC(12,3)`) — trip catches, invoice/purchase line quantities, per
 * `01_PRODUCT_VISION.md`'s NUMERIC(12,3) rule and `06_COMPONENT_LIBRARY.md`
 * §4.
 */
export function QuantityInput({ unit, ...props }: QuantityInputProps) {
  return <NumberInput decimalPlaces={3} suffix={unit} {...props} />;
}
