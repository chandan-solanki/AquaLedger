const DEFAULT_LOCALE = "en-IN";

/**
 * Formats a quantity value at the backend's NUMERIC(12,3) weight precision.
 */
export function formatQuantity(value: string | number): string {
  return formatFixed(value, 3);
}

/**
 * Formats a rate value at the backend's NUMERIC(12,4) rate precision.
 */
export function formatRate(value: string | number): string {
  return formatFixed(value, 4);
}

function formatFixed(value: string | number, decimals: number): string {
  const numeric = typeof value === "string" ? Number(value) : value;

  if (!Number.isFinite(numeric)) {
    return "—";
  }

  return new Intl.NumberFormat(DEFAULT_LOCALE, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(numeric);
}
