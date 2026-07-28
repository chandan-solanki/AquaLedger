import { APP_CONFIG } from "@/constants/app";

/**
 * Formats a money value with the backend's NUMERIC(14,2) precision — always
 * exactly 2 decimals, never rounded/truncated differently than the server.
 * Accepts a string to avoid floating-point drift when the value originates
 * from a Decimal-backed API response.
 */
export function formatCurrency(
  value: string | number,
  currency: string = APP_CONFIG.defaultCurrency,
  locale: string = APP_CONFIG.defaultLocale
): string {
  const numeric = typeof value === "string" ? Number(value) : value;

  if (!Number.isFinite(numeric)) {
    return "—";
  }

  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numeric);
}

/**
 * A short form of `formatCurrency` (e.g. "₹35K", "₹6.1L") for contexts with
 * limited space — chart axis ticks — where `formatCurrency`'s full
 * 2-decimal precision doesn't fit and isn't needed; the exact figure still
 * shows in full via `formatCurrency` wherever precision matters (tooltips,
 * KPI cards, tables).
 */
export function formatCompactCurrency(
  value: string | number,
  currency: string = APP_CONFIG.defaultCurrency,
  locale: string = APP_CONFIG.defaultLocale
): string {
  const numeric = typeof value === "string" ? Number(value) : value;

  if (!Number.isFinite(numeric)) {
    return "—";
  }

  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    notation: "compact",
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
  }).format(numeric);
}
