"use client";

import Link from "next/link";
import {
  Anchor,
  ArrowDownToLine,
  ArrowUpFromLine,
  Building2,
  Route as RouteIcon,
  ShieldAlert,
  Wallet,
} from "lucide-react";

import { NoActivity } from "@/components/feedback/empty-states";
import { EmptyState } from "@/components/feedback/empty-state";
import { InfoCard } from "@/components/data-display/info-card";
import { MetricCard, TrendMetricCard } from "@/components/data-display/metric-card";
import { SummaryGrid } from "@/components/data-display/summary-grid";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { useCurrentUser } from "@/features/auth/hooks/use-current-user";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { useTenant } from "@/features/auth/hooks/use-tenant";
import { formatCurrency } from "@/utils/format-currency";

/**
 * Static mock figures only — no API call, no TanStack Query, per this
 * session's explicit scope. Shapes and labels match the real Dashboard spec
 * (`05_PAGE_CATALOG.md` §2); the real, data-backed version ships once the
 * backend's reporting/aggregation endpoints exist (Sprint 3).
 */
const MOCK_METRICS = {
  receivables: { value: 482650, changePercentage: 6.8, trend: "up" as const },
  payables: { value: 195300, changePercentage: -3.1, trend: "down" as const },
  tripsAtSea: { value: 6, description: "2 returning this week" },
  boatsCompliance: { value: 3, description: "Within the next 30 days" },
};

const QUICK_ACTIONS = [
  { id: "new-company", label: "New Company", href: "/companies/new", icon: Building2, permission: "company:create" },
  { id: "new-trip", label: "New Trip", href: "/trips/new", icon: RouteIcon, permission: "trip:create" },
  { id: "new-invoice", label: "New Invoice", href: "/invoices/new", icon: Wallet, permission: "invoice:create" },
  {
    id: "new-payment",
    label: "New Customer Payment",
    href: "/payments/new",
    icon: ArrowDownToLine,
    permission: "payment:create",
  },
] as const;

/**
 * Still a placeholder — no business API, no TanStack Query wiring (Sprint 1
 * Session 5 scope). Built entirely from this session's and prior sessions'
 * reusable components (`PageHeader`, `SummaryGrid`, `MetricCard`/
 * `TrendMetricCard`, `InfoCard`, `EmptyState`) rather than one-off markup,
 * so swapping the mock figures for real query data later is a data change,
 * not a structural one.
 */
export default function DashboardPage() {
  const user = useCurrentUser();
  const tenant = useTenant();
  const { hasPermission } = usePermissions();

  const visibleQuickActions = QUICK_ACTIONS.filter((action) => hasPermission(action.permission));

  return (
    <PageContainer>
      <PageHeader
        title={`Welcome back, ${user?.fullName ?? ""}`}
        description={
          tenant
            ? `Tenant ${tenant.id} · ${user?.roles.join(", ") || "No roles assigned"}`
            : user?.roles.join(", ") || "No roles assigned"
        }
      />

      <SummaryGrid>
        <TrendMetricCard
          title="Total Receivables Outstanding"
          value={formatCurrency(MOCK_METRICS.receivables.value)}
          icon={ArrowDownToLine}
          changePercentage={MOCK_METRICS.receivables.changePercentage}
          trend={MOCK_METRICS.receivables.trend}
        />
        <TrendMetricCard
          title="Total Payables Outstanding"
          value={formatCurrency(MOCK_METRICS.payables.value)}
          icon={ArrowUpFromLine}
          changePercentage={MOCK_METRICS.payables.changePercentage}
          trend={MOCK_METRICS.payables.trend}
        />
        <MetricCard
          title="Trips Currently at Sea"
          value={String(MOCK_METRICS.tripsAtSea.value)}
          icon={Anchor}
          description={MOCK_METRICS.tripsAtSea.description}
        />
        <MetricCard
          title="Boats with Expiring Compliance"
          value={String(MOCK_METRICS.boatsCompliance.value)}
          icon={ShieldAlert}
          description={MOCK_METRICS.boatsCompliance.description}
        />
      </SummaryGrid>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <InfoCard title="Quick Actions" className="lg:col-span-1">
          <div className="flex flex-col gap-2">
            {visibleQuickActions.length === 0 && (
              <p className="text-sm text-muted-foreground">No quick actions available for your role.</p>
            )}
            {visibleQuickActions.map((action) => (
              <Button key={action.id} variant="outline" className="justify-start" asChild>
                <Link href={action.href}>
                  <action.icon />
                  {action.label}
                </Link>
              </Button>
            ))}
          </div>
        </InfoCard>

        <InfoCard title="Recent Activity" className="lg:col-span-2">
          <NoActivity description="Recent invoices, payments, and trip updates will appear here." />
        </InfoCard>
      </div>

      <InfoCard title="Pending Tasks">
        <EmptyState
          icon={RouteIcon}
          title="No pending tasks"
          description="Draft invoices, unallocated payments, and trips awaiting settlement will appear here."
        />
      </InfoCard>
    </PageContainer>
  );
}
