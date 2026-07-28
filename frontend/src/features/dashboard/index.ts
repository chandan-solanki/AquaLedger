export { DashboardPage } from "@/features/dashboard/pages/dashboard-page";

export { DashboardKpiGrid } from "@/features/dashboard/components/dashboard-kpi-grid";
export { DashboardOperationsCard } from "@/features/dashboard/components/dashboard-operations-card";
export { DashboardFinancialCard } from "@/features/dashboard/components/dashboard-financial-card";
export { DashboardRecentActivityCard } from "@/features/dashboard/components/dashboard-recent-activity-card";
export { DashboardAlertsCard } from "@/features/dashboard/components/dashboard-alerts-card";
export { DashboardQuickActionsMenu } from "@/features/dashboard/components/dashboard-quick-actions-menu";
export { DashboardMonthlySalesChart } from "@/features/dashboard/components/dashboard-monthly-sales-chart";
export { DashboardMonthlyPurchasesChart } from "@/features/dashboard/components/dashboard-monthly-purchases-chart";
export { DashboardFishSalesChart } from "@/features/dashboard/components/dashboard-fish-sales-chart";
export { DashboardTripStatusChart } from "@/features/dashboard/components/dashboard-trip-status-chart";
export { DashboardTopCustomersCard } from "@/features/dashboard/components/dashboard-top-customers-card";
export { DashboardTopSuppliersCard } from "@/features/dashboard/components/dashboard-top-suppliers-card";
export { DashboardTopFishCard } from "@/features/dashboard/components/dashboard-top-fish-card";
export { DashboardOutstandingSummaryCard } from "@/features/dashboard/components/dashboard-outstanding-summary-card";

export { useDashboard } from "@/features/dashboard/hooks/use-dashboard";

export { dashboardService } from "@/features/dashboard/services/dashboard-service";

export type {
  BackendDashboardResponse,
  DashboardActivityItem,
  DashboardActivityType,
  DashboardAlert,
  DashboardAlertType,
  DashboardCharts,
  DashboardData,
  DashboardFinancial,
  DashboardKpis,
  DashboardOperations,
  DashboardTripStatusLabel,
  DashboardTripStatusPoint,
  DashboardWidgets,
  FishSalesPoint,
  MonthlyPurchasesPoint,
  MonthlySalesPoint,
  OutstandingSummary,
  TopCustomerWidgetItem,
  TopFishWidgetItem,
  TopSupplierWidgetItem,
} from "@/features/dashboard/types/dashboard";
export { mapBackendDashboard } from "@/features/dashboard/types/dashboard";

export { dashboardKeys } from "@/features/dashboard/constants/query-keys";

export {
  ACTIVITY_TYPE_BADGE_VARIANT,
  ACTIVITY_TYPE_ICONS,
  ACTIVITY_TYPE_LABELS,
} from "@/features/dashboard/constants/activity-type";
export {
  ALERT_TYPE_ICONS,
  ALERT_TYPE_LABELS,
  ALERT_TYPE_SEVERITY,
  type DashboardAlertSeverity,
} from "@/features/dashboard/constants/alert-type";
