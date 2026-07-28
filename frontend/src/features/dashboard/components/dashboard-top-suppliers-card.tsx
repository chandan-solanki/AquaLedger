"use client";

import { Truck } from "lucide-react";
import { useRouter } from "next/navigation";
import { memo, useMemo } from "react";

import { DashboardMiniTable } from "@/components/dashboard/DashboardMiniTable";
import type { DashboardMiniTableColumn } from "@/components/dashboard/DashboardMiniTable";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { TopSupplierWidgetItem } from "@/features/dashboard/types/dashboard";
import { formatCurrency } from "@/utils/format-currency";

interface DashboardTopSuppliersCardProps {
  items: TopSupplierWidgetItem[];
  className?: string;
}

/**
 * TASKS.md Sprint 10 Session 4 "WIDGET 2 Top Suppliers" - mirrors
 * DashboardTopCustomersCard on the buy side. `/suppliers/{id}` already
 * exists, so rows are clickable for callers with `supplier:view`.
 */
function DashboardTopSuppliersCardImpl({ items, className }: DashboardTopSuppliersCardProps) {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const canView = hasPermission("supplier:view");

  const columns = useMemo<DashboardMiniTableColumn<TopSupplierWidgetItem>[]>(
    () => [
      {
        key: "supplier",
        header: "Supplier",
        render: (row) => <span className="font-medium">{row.supplierName}</span>,
      },
      { key: "purchases", header: "Purchases", align: "right", render: (row) => formatCurrency(row.purchaseTotal) },
      {
        key: "outstanding",
        header: "Outstanding",
        align: "right",
        render: (row) => formatCurrency(row.outstandingAmount),
      },
      { key: "bills", header: "Bills", align: "right", render: (row) => row.purchaseBillCount },
    ],
    []
  );

  return (
    <DashboardMiniTable
      title="Top Suppliers"
      columns={columns}
      rows={items}
      rowKey={(row) => row.supplierId}
      onRowClick={canView ? (row) => router.push(`/suppliers/${row.supplierId}`) : undefined}
      emptyIcon={Truck}
      emptyMessage="No supplier purchases recorded yet."
      className={className}
    />
  );
}

export const DashboardTopSuppliersCard = memo(DashboardTopSuppliersCardImpl);
