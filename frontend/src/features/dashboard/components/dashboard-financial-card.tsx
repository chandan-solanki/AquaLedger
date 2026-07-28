import { memo } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DashboardFinancial, DashboardKpis } from "@/features/dashboard/types/dashboard";
import { formatCurrency } from "@/utils/format-currency";

interface DashboardFinancialCardProps {
  financial: DashboardFinancial;
  /** `draft_invoices`/`draft_payments` are backend `kpis` fields, not `financial` ones — grouped here only for presentation, per TASKS.md Sprint 10 Session 2's "FINANCIAL CARD" spec. Still read verbatim, never recomputed. */
  kpis: DashboardKpis;
  className?: string;
}

interface FigureRowProps {
  label: string;
  value: string;
}

function FigureRow({ label, value }: FigureRowProps) {
  return (
    <div className="flex items-center justify-between py-2 first:pt-0 last:pb-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-semibold tabular-nums">{value}</span>
    </div>
  );
}

/**
 * The Dashboard's Financial Row card, per TASKS.md Sprint 10 Session 2's
 * "FINANCIAL CARD" spec: Outstanding (customer + supplier, kept separate —
 * never summed into one number client-side), draft invoices/payments, and
 * this month's issued invoices/purchase bills. Every figure is read
 * straight from the backend response.
 */
function DashboardFinancialCardImpl({ financial, kpis, className }: DashboardFinancialCardProps) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Financial Summary</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="divide-y">
          <FigureRow label="Customer Outstanding" value={formatCurrency(financial.customerOutstanding)} />
          <FigureRow label="Supplier Outstanding" value={formatCurrency(financial.supplierOutstanding)} />
          <FigureRow label="Draft Invoices" value={String(kpis.draftInvoices)} />
          <FigureRow label="Draft Payments" value={String(kpis.draftPayments)} />
          <FigureRow label="Invoices Issued This Month" value={String(financial.invoicesIssuedThisMonth)} />
          <FigureRow label="Purchase Bills This Month" value={String(financial.purchaseBillsThisMonth)} />
        </div>
      </CardContent>
    </Card>
  );
}

export const DashboardFinancialCard = memo(DashboardFinancialCardImpl);
