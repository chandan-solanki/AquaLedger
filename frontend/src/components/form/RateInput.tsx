"use client";

import { NumberInput, type NumberInputProps } from "./NumberInput";

export interface RateInputProps extends Omit<NumberInputProps, "decimalPlaces"> {
  /** e.g. "/kg" — rendered as a trailing suffix. */
  unit?: string;
}

/**
 * A Number Input variant fixed to the backend's rate precision
 * (`NUMERIC(12,4)`) — invoice/purchase line rates, per `01_PRODUCT_VISION.md`'s
 * NUMERIC(12,4) rule and `06_COMPONENT_LIBRARY.md` §4.
 */
export function RateInput({ unit, ...props }: RateInputProps) {
  return <NumberInput decimalPlaces={4} suffix={unit} {...props} />;
}
