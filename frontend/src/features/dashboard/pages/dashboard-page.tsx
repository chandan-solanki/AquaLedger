"use client";

import { RefreshCw } from "lucide-react";
import { useMemo } from "react";

import { DashboardSkeleton } from "@/components/feedback/skeletons/dashboard-skeleton";
import { ErrorState } from "@/components/feedback/error-state";
import { Forbidden } from "@/components/feedback/error-states";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { DashboardAlertsCard } from "@/features/dashboard/components/dashboard-alerts-card";
import { DashboardFinancialCard } from "@/features/dashboard/components/dashboard-financial-card";
import { DashboardFishSalesChart } from "@/features/dashboard/components/dashboard-fish-sales-chart";
import { DashboardKpiGrid } from "@/features/dashboard/components/dashboard-kpi-grid";
import { DashboardMonthlyPurchasesChart } from "@/features/dashboard/components/dashboard-monthly-purchases-chart";
import { DashboardMonthlySalesChart } from "@/features/dashboard/components/dashboard-monthly-sales-chart";
import { DashboardOperationsCard } from "@/features/dashboard/components/dashboard-operations-card";
import { DashboardOutstandingSummaryCard } from "@/features/dashboard/components/dashboard-outstanding-summary-card";
import { DashboardQuickActionsMenu } from "@/features/dashboard/components/dashboard-quick-actions-menu";
import { DashboardRecentActivityCard } from "@/features/dashboard/components/dashboard-recent-activity-card";
import { DashboardTopCustomersCard } from "@/features/dashboard/components/dashboard-top-customers-card";
import { DashboardTopFishCard } from "@/features/dashboard/components/dashboard-top-fish-card";
import { DashboardTopSuppliersCard } from "@/features/dashboard/components/dashboard-top-suppliers-card";
import { DashboardTripStatusChart } from "@/features/dashboard/components/dashboard-trip-status-chart";
import { useDashboard } from "@/features/dashboard/hooks/use-dashboard";
import { normalizeApiError } from "@/utils/api-error";
import { formatDate } from "@/utils/format-date";
import { cn } from "@/lib/utils";

/**
 * The owner's homepage — a single consolidated, read-only view built
 * entirely from the backend's GET /dashboard response (TASKS.md Sprint 10
 * Session 1, extended with a `charts` section in Session 3 and a
 * `widgets` section — top customers/suppliers/fish, outstanding summary —
 * in Session 4). This page never aggregates invoices/payments/trips/
 * catches/purchase bills itself; every number, chart series and widget
 * row rendered below is read straight off `useDashboard()`'s data, only
 * formatted/reshaped for display.
 *
 * Loading is a single full-page `DashboardSkeleton` (shaped to match this
 * exact layout, so nothing shifts once data arrives) rather than a spinner.
 * A first-load failure replaces the page with a full `ErrorState`/
 * `Forbidden`; a failed *background* refresh (the 5-minute auto-stale
 * refetch, or the manual Refresh button) instead keeps the last-known-good
 * data on screen with a small inline error banner — a full-page wipe on
 * every transient refresh failure would be worse than showing slightly
 * stale numbers with a clear "couldn't refresh" notice.
 */
export function DashboardPage() {
  const query = useDashboard();
  const apiError = query.isError ? normalizeApiError(query.error) : null;
  const data = query.data;
  const today = useMemo(() => formatDate(new Date()), []);

  if (query.isLoading) {
    return (
      <PageContainer>
        <DashboardSkeleton />
      </PageContainer>
    );
  }

  if (apiError && !data) {
    if (apiError.category === "forbidden") {
      return (
        <PageContainer>
          <Forbidden description="You don't have permission to view the dashboard. Contact an administrator if you believe this is a mistake." />
        </PageContainer>
      );
    }
    return (
      <PageContainer>
        <ErrorState
          title="Failed to load the dashboard"
          description={apiError.message}
          onRetry={() => query.refetch()}
        />
      </PageContainer>
    );
  }

  if (!data) return null;

  return (
    <PageContainer>
      <PageHeader
        title="Dashboard"
        description={today}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Refresh dashboard"
              onClick={() => query.refetch()}
              disabled={query.isFetching}
            >
              <RefreshCw
                className={cn("size-4", query.isFetching && "animate-spin motion-reduce:animate-none")}
                aria-hidden
              />
            </Button>
            <DashboardQuickActionsMenu />
          </div>
        }
      />

      {apiError && (
        <ErrorState
          variant="inline"
          title="Couldn't refresh the dashboard"
          description={`Showing the last-loaded data. ${apiError.message}`}
          onRetry={() => query.refetch()}
        />
      )}

      <DashboardKpiGrid data={data} />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <DashboardMonthlySalesChart data={data.charts.monthlySales} />
        <DashboardMonthlyPurchasesChart data={data.charts.monthlyPurchases} />
        <DashboardFishSalesChart data={data.charts.fishSales} />
        <DashboardTripStatusChart data={data.charts.tripStatus} />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <DashboardTopCustomersCard items={data.widgets.topCustomers} />
        <DashboardTopSuppliersCard items={data.widgets.topSuppliers} />
        <DashboardTopFishCard items={data.widgets.topFish} />
        <DashboardOutstandingSummaryCard summary={data.widgets.outstandingSummary} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <DashboardOperationsCard operations={data.operations} />
        <DashboardFinancialCard financial={data.financial} kpis={data.kpis} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <DashboardRecentActivityCard items={data.recentActivity} />
        <DashboardAlertsCard alerts={data.alerts} />
      </div>
    </PageContainer>
  );
}
