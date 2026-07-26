import { SummaryGrid } from "@/components/data-display/summary-grid";
import { KpiCard, type KpiCardProps } from "@/components/charts/KpiCard";

export interface ReportSummaryItem extends KpiCardProps {
  key: string;
}

export interface ReportSummaryProps {
  items: ReportSummaryItem[];
  columns?: 2 | 3 | 4;
  className?: string;
}

/** A Report page's KPI row — composes the shared `SummaryGrid` layout with `KpiCard`s, rather than a report-specific grid implementation. */
export function ReportSummary({ items, columns = 4, className }: ReportSummaryProps) {
  return (
    <SummaryGrid columns={columns} className={className}>
      {items.map(({ key, ...kpi }) => (
        <KpiCard key={key} {...kpi} />
      ))}
    </SummaryGrid>
  );
}
