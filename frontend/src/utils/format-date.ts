import { format, formatDistanceToNow, parseISO } from "date-fns";

const DATE_FORMAT = "dd MMM yyyy";
const DATE_TIME_FORMAT = "dd MMM yyyy, hh:mm a";
const MONTH_FORMAT = "MMM yyyy";

function toDate(value: string | Date): Date {
  return typeof value === "string" ? parseISO(value) : value;
}

export function formatDate(value: string | Date): string {
  return format(toDate(value), DATE_FORMAT);
}

export function formatDateTime(value: string | Date): string {
  return format(toDate(value), DATE_TIME_FORMAT);
}

export function formatRelativeTime(value: string | Date): string {
  return formatDistanceToNow(toDate(value), { addSuffix: true });
}

/** e.g. "Jul 2026" — for chart axis labels/tooltips over a month-bucketed series. */
export function formatMonth(value: string | Date): string {
  return format(toDate(value), MONTH_FORMAT);
}
