"use client";

import { Anchor, Banknote, Fish, Landmark, Receipt, Route as RouteIcon, TrendingUp, Wallet } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { memo, useMemo } from "react";

import { MetricGrid } from "@/components/dashboard/MetricGrid";
import { MetricCard } from "@/components/data-display/metric-card";
import type { DashboardData } from "@/features/dashboard/types/dashboard";
import { formatCurrency } from "@/utils/format-currency";
import { formatQuantity } from "@/utils/format-number";

interface DashboardKpiGridProps {
  data: DashboardData;
}

interface KpiCardDefinition {
  key: string;
  title: string;
  value: string;
  description: string;
  icon: LucideIcon;
}

/**
 * The Dashboard's 8-card KPI row, per TASKS.md Sprint 10 Session 2's "KPI
 * GRID" spec. `MetricGrid` (a `SummaryGrid` alias) already reflows
 * 4 → 2 → 1 columns at the exact breakpoints requested (desktop/tablet/
 * mobile) — this component only decides what each card shows, never how
 * the grid itself behaves. Every value is read straight off the backend
 * response and formatted for display; no totals are computed here.
 */
function DashboardKpiGridImpl({ data }: DashboardKpiGridProps) {
  const cards = useMemo<KpiCardDefinition[]>(() => {
    const { kpis, financial } = data;
    return [
      {
        key: "todays-sales",
        title: "Today's Sales",
        value: formatCurrency(kpis.todaysSales),
        description: "Invoices issued today",
        icon: Receipt,
      },
      {
        key: "monthly-sales",
        title: "Monthly Sales",
        value: formatCurrency(kpis.monthlySales),
        description: "Month to date",
        icon: TrendingUp,
      },
      {
        key: "payments-received-today",
        title: "Payments Received Today",
        value: formatCurrency(kpis.customerPaymentsToday),
        description: "From customers",
        icon: Wallet,
      },
      {
        key: "supplier-payments-today",
        title: "Supplier Payments Today",
        value: formatCurrency(kpis.supplierPaymentsToday),
        description: "To suppliers",
        icon: Banknote,
      },
      {
        key: "active-trips",
        title: "Active Trips",
        value: String(kpis.activeTrips),
        description: `${kpis.boatsAtSea} boat(s) currently at sea`,
        icon: RouteIcon,
      },
      {
        key: "boats-at-sea",
        title: "Boats At Sea",
        value: String(kpis.boatsAtSea),
        description: "Out on an active trip",
        icon: Anchor,
      },
      {
        key: "todays-catch",
        title: "Today's Catch",
        value: formatQuantity(kpis.todaysCatchQuantity),
        description: "Landed today, across all trips",
        icon: Fish,
      },
      {
        key: "outstanding-customers",
        title: "Outstanding Customers",
        value: formatCurrency(financial.customerOutstanding),
        description: "Total receivable",
        icon: Landmark,
      },
    ];
  }, [data]);

  return (
    <MetricGrid columns={4}>
      {cards.map((card) => (
        <MetricCard
          key={card.key}
          title={card.title}
          value={card.value}
          description={card.description}
          icon={card.icon}
        />
      ))}
    </MetricGrid>
  );
}

export const DashboardKpiGrid = memo(DashboardKpiGridImpl);
