"use client";

import { APP_CONFIG } from "@/constants/app";

import { NumberInput, type NumberInputProps } from "./NumberInput";

export interface CurrencyInputProps
  extends Omit<NumberInputProps, "decimalPlaces" | "prefix" | "suffix"> {
  currency?: string;
  locale?: string;
}

function getCurrencySymbol(currency: string, locale: string): string {
  const part = new Intl.NumberFormat(locale, { style: "currency", currency })
    .formatToParts(0)
    .find((p) => p.type === "currency");
  return part?.value ?? currency;
}

/**
 * A Number Input variant fixed to the tenant's currency and the backend's
 * exact decimal precision (`NUMERIC(14,2)`), per `06_COMPONENT_LIBRARY.md`
 * §4 — the single most business-critical form component in AquaLedger,
 * since every money field in the product renders through it. Uses the same
 * locale/currency defaults as `formatCurrency()` (`utils/format-currency.ts`)
 * so the editable and read-only (Money Display) renderings of a value never
 * drift apart from each other.
 */
export function CurrencyInput({
  currency = APP_CONFIG.defaultCurrency,
  locale = APP_CONFIG.defaultLocale,
  ...props
}: CurrencyInputProps) {
  return (
    <NumberInput
      decimalPlaces={2}
      prefix={getCurrencySymbol(currency, locale)}
      inputMode="decimal"
      {...props}
    />
  );
}
