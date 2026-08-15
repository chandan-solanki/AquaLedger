import { ArrowDownToLine, ArrowUpFromLine, FileText, Receipt, Wallet } from "lucide-react";

import { SummaryGrid } from "@/components/data-display/summary-grid";
import { MetricCard } from "@/components/data-display/metric-card";
import type { CustomerLedgerSummary } from "@/features/reports/types/customer-ledger";
import { formatCurrency } from "@/utils/format-currency";

interface CustomerLedgerSummaryCardsProps {
  summary: CustomerLedgerSummary;
}

/**
 * The Customer Ledger's Summary KPI row - six figures, every one already
 * computed server-side (ReportsService.get_customer_ledger) and rendered
 * here as-is, never recomputed client-side (ARCHITECTURE.md §3.4/§10:
 * "backend performs all calculations"). Uses the shared `SummaryGrid`/
 * `MetricCard` primitives - the same ones `ReportPageTemplate`'s own doc
 * comment names as the intended Report-page KPI row - rather than a new
 * bespoke card layout.
 */
export function CustomerLedgerSummaryCards({ summary }: CustomerLedgerSummaryCardsProps) {
  return (
    <SummaryGrid columns={3}>
      <MetricCard
        title="Opening Balance"
        value={formatCurrency(summary.openingBalance)}
        icon={Wallet}
      />
      <MetricCard
        title="Total Debit"
        value={formatCurrency(summary.totalDebit)}
        icon={ArrowUpFromLine}
      />
      <MetricCard
        title="Total Credit"
        value={formatCurrency(summary.totalCredit)}
        icon={ArrowDownToLine}
      />
      <MetricCard
        title="Closing Balance"
        value={formatCurrency(summary.closingBalance)}
        icon={Wallet}
      />
      <MetricCard title="Invoice Count" value={String(summary.invoiceCount)} icon={FileText} />
      <MetricCard title="Payment Count" value={String(summary.paymentCount)} icon={Receipt} />
    </SummaryGrid>
  );
}
