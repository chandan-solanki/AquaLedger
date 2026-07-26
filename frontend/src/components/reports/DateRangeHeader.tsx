import { format } from "date-fns";
import { CalendarDays } from "lucide-react";
import type { DateRange } from "react-day-picker";

import { DEFAULT_DATE_FORMAT } from "@/lib/date-format";
import { cn } from "@/lib/utils";

export interface DateRangeHeaderProps {
  range?: DateRange;
  dateFormat?: string;
  label?: string;
  className?: string;
}

/** A read-only "covering {range}" caption for a Report/Dashboard section — display only, not an input; `ReportFilters`/`DateRangeFilter` own the actual editing control. */
export function DateRangeHeader({ range, dateFormat = DEFAULT_DATE_FORMAT, label, className }: DateRangeHeaderProps) {
  const text = range?.from
    ? range.to
      ? `${format(range.from, dateFormat)} – ${format(range.to, dateFormat)}`
      : format(range.from, dateFormat)
    : "All time";

  return (
    <span className={cn("inline-flex items-center gap-1.5 text-sm text-muted-foreground", className)}>
      <CalendarDays className="size-4" aria-hidden />
      {label ? `${label}: ${text}` : text}
    </span>
  );
}
