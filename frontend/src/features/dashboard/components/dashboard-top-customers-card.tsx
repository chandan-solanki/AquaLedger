"use client";

import { Users } from "lucide-react";
import { useRouter } from "next/navigation";
import { memo, useMemo } from "react";

import { DashboardMiniTable } from "@/components/dashboard/DashboardMiniTable";
import type { DashboardMiniTableColumn } from "@/components/dashboard/DashboardMiniTable";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { TopCustomerWidgetItem } from "@/features/dashboard/types/dashboard";
import { formatCurrency } from "@/utils/format-currency";

interface DashboardTopCustomersCardProps {
  items: TopCustomerWidgetItem[];
  className?: string;
}

/**
 * TASKS.md Sprint 10 Session 4 "WIDGET 1 Top Customers" - a compact table
 * over the backend's already-sorted top-5-by-sales list. Rows navigate to
 * `/companies/{id}` (a route that already exists) only for callers with
 * `company:view` - never invented, per the session's "do not invent
 * routes" rule.
 */
function DashboardTopCustomersCardImpl({ items, className }: DashboardTopCustomersCardProps) {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const canView = hasPermission("company:view");

  const columns = useMemo<DashboardMiniTableColumn<TopCustomerWidgetItem>[]>(
    () => [
      { key: "customer", header: "Customer", render: (row) => <span className="font-medium">{row.companyName}</span> },
      { key: "sales", header: "Sales", align: "right", render: (row) => formatCurrency(row.totalSales) },
      {
        key: "outstanding",
        header: "Outstanding",
        align: "right",
        render: (row) => formatCurrency(row.outstandingAmount),
      },
      { key: "invoices", header: "Invoices", align: "right", render: (row) => row.invoiceCount },
    ],
    []
  );

  return (
    <DashboardMiniTable
      title="Top Customers"
      columns={columns}
      rows={items}
      rowKey={(row) => row.companyId}
      onRowClick={canView ? (row) => router.push(`/companies/${row.companyId}`) : undefined}
      emptyIcon={Users}
      emptyMessage="No customer sales recorded yet."
      className={className}
    />
  );
}

export const DashboardTopCustomersCard = memo(DashboardTopCustomersCardImpl);
