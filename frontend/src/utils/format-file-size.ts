const UNITS = ["B", "KB", "MB", "GB"] as const;

/**
 * Formats a byte count as a short, human-readable size (e.g. "42 KB",
 * "1.2 MB") — sibling to `format-currency.ts`/`format-date.ts`. Uses binary
 * (1024-based) steps, matching how file sizes are conventionally displayed
 * in OS file managers and browser download UIs. Whole-unit values render
 * with no decimal (e.g. "48 KB"); everything else keeps one decimal place.
 */
export function formatFileSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return "—";
  if (bytes === 0) return "0 B";

  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), UNITS.length - 1);
  const value = bytes / 1024 ** exponent;
  const formatted = Number.isInteger(value) ? value.toString() : value.toFixed(1);

  return `${formatted} ${UNITS[exponent]}`;
}
