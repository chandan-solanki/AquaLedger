import { memo } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { OutstandingSummary } from "@/features/dashboard/types/dashboard";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/utils/format-currency";

interface DashboardOutstandingSummaryCardProps {
  summary: OutstandingSummary;
  className?: string;
}

interface FigureProps {
  label: string;
  value: string;
  /** Overdue figures render destructive-red per TASKS.md Sprint 10 Session 4's "Highlight overdue values". */
  highlight?: boolean;
}

function Figure({ label, value, highlight }: FigureProps) {
  return (
    <div className="space-y-1 rounded-lg border p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={cn("text-lg font-semibold tabular-nums", highlight && "text-destructive")}>{value}</p>
    </div>
  );
}

/**
 * TASKS.md Sprint 10 Session 4 "WIDGET 4 Outstanding Summary" - four
 * already-backend-computed figures (customer/supplier outstanding and
 * their overdue subsets), never derived client-side.
 */
function DashboardOutstandingSummaryCardImpl({ summary, className }: DashboardOutstandingSummaryCardProps) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Outstanding Summary</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3">
          <Figure label="Customer Outstanding" value={formatCurrency(summary.customerOutstanding)} />
          <Figure label="Supplier Outstanding" value={formatCurrency(summary.supplierOutstanding)} />
          <Figure label="Customer Overdue" value={formatCurrency(summary.customerOverdue)} highlight />
          <Figure label="Supplier Overdue" value={formatCurrency(summary.supplierOverdue)} highlight />
        </div>
      </CardContent>
    </Card>
  );
}

export const DashboardOutstandingSummaryCard = memo(DashboardOutstandingSummaryCardImpl);
