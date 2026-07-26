"use client";

import { FilterPanel, type FilterPanelProps } from "@/components/filters/FilterPanel";

export type ReportFiltersProps = FilterPanelProps;

/** A Report page's filter row — a `FilterPanel` configured with report-appropriate defaults (open by default, "Report Filters" title) rather than a separate implementation. */
export function ReportFilters({ title = "Report Filters", ...props }: ReportFiltersProps) {
  return <FilterPanel title={title} {...props} />;
}
