import { ArrowDownToLine, ArrowUpFromLine, Scale, Users, Wallet } from "lucide-react";

import { SummaryGrid } from "@/components/data-display/summary-grid";
import { MetricCard } from "@/components/data-display/metric-card";
import type { OutstandingReportSummary } from "@/features/reports/types/outstanding-report";
import { formatCurrency } from "@/utils/format-currency";

interface OutstandingReportSummaryCardsProps {
  summary: OutstandingReportSummary;
}

/**
 * The Outstanding Report's Summary KPI row - seven figures (TASKS.md
 * Sprint 11 Session 3 Phase B), always the full AR/AP picture regardless
 * of which tab (`entityType`) is active - see
 * ReportsService.get_outstanding_report's own docstring.
 */
export function OutstandingReportSummaryCards({ summary }: OutstandingReportSummaryCardsProps) {
  return (
    <SummaryGrid columns={3}>
      <MetricCard
        title="Accounts Receivable"
        value={formatCurrency(summary.accountsReceivable)}
        icon={ArrowUpFromLine}
      />
      <MetricCard
        title="Accounts Payable"
        value={formatCurrency(summary.accountsPayable)}
        icon={ArrowDownToLine}
      />
      <MetricCard title="Net Position" value={formatCurrency(summary.netPosition)} icon={Scale} />
      <MetricCard
        title="Overdue Receivable"
        value={formatCurrency(summary.overdueReceivable)}
        icon={Wallet}
      />
      <MetricCard
        title="Overdue Payable"
        value={formatCurrency(summary.overduePayable)}
        icon={Wallet}
      />
      <MetricCard
        title="Customers With Outstanding"
        value={String(summary.customersWithOutstanding)}
        icon={Users}
      />
      <MetricCard
        title="Suppliers With Outstanding"
        value={String(summary.suppliersWithOutstanding)}
        icon={Users}
      />
    </SummaryGrid>
  );
}
