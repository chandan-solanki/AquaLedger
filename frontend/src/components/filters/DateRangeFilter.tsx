"use client";

import type { DateRange } from "react-day-picker";

import { DateRangePicker } from "@/components/form/DateRangePicker";

export interface DateRangeFilterProps {
  label?: string;
  value?: DateRange;
  onChange: (range: DateRange | undefined) => void;
  placeholder?: string;
  className?: string;
}

/**
 * The filter-bar configuration of `components/form`'s `DateRangePicker` —
 * Start/End plus Clear (built into the picker's own popover footer), per
 * `06_COMPONENT_LIBRARY.md` §6's date-range filter. Reused rather than
 * reimplemented, per the reuse-over-duplication rule in
 * `06_COMPONENT_LIBRARY.md` §19.
 */
export function DateRangeFilter({
  label,
  value,
  onChange,
  placeholder = "Any date",
  className,
}: DateRangeFilterProps) {
  return (
    <DateRangePicker
      label={label}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      containerClassName={className}
    />
  );
}
