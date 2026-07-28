"use client";

import { Fish } from "lucide-react";
import { useRouter } from "next/navigation";
import { memo, useMemo } from "react";

import { DashboardMiniTable } from "@/components/dashboard/DashboardMiniTable";
import type { DashboardMiniTableColumn } from "@/components/dashboard/DashboardMiniTable";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import type { TopFishWidgetItem } from "@/features/dashboard/types/dashboard";
import { formatCurrency } from "@/utils/format-currency";
import { formatQuantity } from "@/utils/format-number";

interface DashboardTopFishCardProps {
  items: TopFishWidgetItem[];
  className?: string;
}

/**
 * TASKS.md Sprint 10 Session 4 "WIDGET 3 Top Fish" - top 5 by sales value.
 * `/fish/{id}` already exists, so rows are clickable for callers with
 * `fish:view`.
 */
function DashboardTopFishCardImpl({ items, className }: DashboardTopFishCardProps) {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const canView = hasPermission("fish:view");

  const columns = useMemo<DashboardMiniTableColumn<TopFishWidgetItem>[]>(
    () => [
      { key: "fish", header: "Fish", render: (row) => <span className="font-medium">{row.fishName}</span> },
      {
        key: "quantity",
        header: "Quantity Sold",
        align: "right",
        render: (row) => formatQuantity(row.quantitySold),
      },
      { key: "sales", header: "Sales Amount", align: "right", render: (row) => formatCurrency(row.salesAmount) },
    ],
    []
  );

  return (
    <DashboardMiniTable
      title="Top Fish"
      columns={columns}
      rows={items}
      rowKey={(row) => row.fishId}
      onRowClick={canView ? (row) => router.push(`/fish/${row.fishId}`) : undefined}
      emptyIcon={Fish}
      emptyMessage="No fish sales recorded yet."
      className={className}
    />
  );
}

export const DashboardTopFishCard = memo(DashboardTopFishCardImpl);
