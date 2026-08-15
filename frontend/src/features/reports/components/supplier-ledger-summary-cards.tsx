import { ArrowDownToLine, ArrowUpFromLine, FileText, Receipt, Wallet } from "lucide-react";

import { SummaryGrid } from "@/components/data-display/summary-grid";
import { MetricCard } from "@/components/data-display/metric-card";
import type { SupplierLedgerSummary } from "@/features/reports/types/supplier-ledger";
import { formatCurrency } from "@/utils/format-currency";

interface SupplierLedgerSummaryCardsProps {
  summary: SupplierLedgerSummary;
}

/**
 * The Supplier Ledger's Summary KPI row - six figures, every one already
 * computed server-side (ReportsService.get_supplier_ledger) and rendered
 * here as-is, never recomputed client-side. Mirrors
 * `CustomerLedgerSummaryCards` exactly, on the buy side.
 */
export function SupplierLedgerSummaryCards({ summary }: SupplierLedgerSummaryCardsProps) {
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
      <MetricCard
        title="Purchase Bill Count"
        value={String(summary.purchaseBillCount)}
        icon={FileText}
      />
      <MetricCard
        title="Supplier Payment Count"
        value={String(summary.supplierPaymentCount)}
        icon={Receipt}
      />
    </SummaryGrid>
  );
}
