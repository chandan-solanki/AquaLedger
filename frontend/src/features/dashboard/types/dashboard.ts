/** Mirrors the backend's ActivityType enum (app/modules/dashboard/constants.py). */
export type DashboardActivityType = "invoice" | "payment" | "trip" | "purchase_bill" | "supplier_payment";

/** Mirrors the backend's AlertType enum (app/modules/dashboard/constants.py) — a closed, six-member set. */
export type DashboardAlertType =
  | "boat_license_expiring"
  | "boat_insurance_expiring"
  | "invoice_overdue"
  | "purchase_bill_overdue"
  | "draft_invoice_stale"
  | "draft_payment_stale";

/**
 * Raw backend shape (snake_case), matching DashboardKPIs
 * (app/modules/dashboard/schemas.py) exactly. Money fields are strings —
 * the backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1) — kept as-is rather than parsed into a JS number.
 */
export interface BackendDashboardKpis {
  todays_sales: string;
  monthly_sales: string;
  customer_payments_today: string;
  supplier_payments_today: string;
  active_trips: number;
  boats_at_sea: number;
  todays_catch_quantity: string;
  draft_invoices: number;
  draft_payments: number;
}

/** Matches DashboardOperations (app/modules/dashboard/schemas.py) exactly. */
export interface BackendDashboardOperations {
  trips_today: number;
  trips_active: number;
  trips_completed_today: number;
  boats_available: number;
  boats_at_sea: number;
  boats_maintenance: number;
}

/** Matches DashboardFinancial (app/modules/dashboard/schemas.py) exactly. */
export interface BackendDashboardFinancial {
  customer_outstanding: string;
  supplier_outstanding: string;
  invoices_issued_this_month: number;
  purchase_bills_this_month: number;
}

/** Matches RecentActivityItem (app/modules/dashboard/schemas.py) exactly. */
export interface BackendDashboardActivityItem {
  type: DashboardActivityType;
  reference: string;
  title: string;
  created_at: string;
}

/** Matches AlertItem (app/modules/dashboard/schemas.py) exactly. */
export interface BackendDashboardAlert {
  type: DashboardAlertType;
  count: number;
  message: string;
}

/** Mirrors the backend's TripStatusChartLabel Literal (app/modules/dashboard/schemas.py) — a relabeling of the trips module's four real statuses for chart display, never invented. */
export type DashboardTripStatusLabel = "Active" | "Completed" | "Cancelled" | "Draft";

/** Matches MonthlySalesPoint (app/modules/dashboard/schemas.py) exactly — one point of the trailing-12-month series, zero-filled server-side. */
export interface BackendMonthlySalesPoint {
  month: string;
  sales_amount: string;
  invoice_count: number;
}

/** Matches MonthlyPurchasesPoint (app/modules/dashboard/schemas.py) exactly. */
export interface BackendMonthlyPurchasesPoint {
  month: string;
  purchase_amount: string;
  purchase_bill_count: number;
}

/** Matches FishSalesPoint (app/modules/dashboard/schemas.py) exactly — top 10 fish by `sales_amount`, already ordered descending server-side. */
export interface BackendFishSalesPoint {
  fish_name: string;
  quantity_sold: string;
  sales_amount: string;
}

/** Matches TripStatusPoint (app/modules/dashboard/schemas.py) exactly — always all four labels, zero-filled server-side. */
export interface BackendDashboardTripStatusPoint {
  status: DashboardTripStatusLabel;
  count: number;
}

/** Matches DashboardCharts (app/modules/dashboard/schemas.py) exactly. */
export interface BackendDashboardCharts {
  monthly_sales: BackendMonthlySalesPoint[];
  monthly_purchases: BackendMonthlyPurchasesPoint[];
  fish_sales: BackendFishSalesPoint[];
  trip_status: BackendDashboardTripStatusPoint[];
}

/** Matches TopCustomerItem (app/modules/dashboard/schemas.py) exactly. */
export interface BackendTopCustomerItem {
  company_id: string;
  company_name: string;
  total_sales: string;
  invoice_count: number;
  outstanding_amount: string;
}

/** Matches TopSupplierItem (app/modules/dashboard/schemas.py) exactly. */
export interface BackendTopSupplierItem {
  supplier_id: string;
  supplier_name: string;
  purchase_total: string;
  purchase_bill_count: number;
  outstanding_amount: string;
}

/** Matches TopFishItem (app/modules/dashboard/schemas.py) exactly. */
export interface BackendTopFishItem {
  fish_id: string;
  fish_name: string;
  quantity_sold: string;
  sales_amount: string;
}

/** Matches OutstandingSummary (app/modules/dashboard/schemas.py) exactly. */
export interface BackendOutstandingSummary {
  customer_outstanding: string;
  customer_overdue: string;
  supplier_outstanding: string;
  supplier_overdue: string;
}

/** Matches DashboardWidgets (app/modules/dashboard/schemas.py) exactly. */
export interface BackendDashboardWidgets {
  top_customers: BackendTopCustomerItem[];
  top_suppliers: BackendTopSupplierItem[];
  top_fish: BackendTopFishItem[];
  outstanding_summary: BackendOutstandingSummary;
}

/**
 * The full GET /dashboard response body (app/modules/dashboard/schemas.py's
 * DashboardResponse). Five sections plus `charts`, all computed server-side
 * — this client never aggregates invoices/payments/trips/catches/purchase
 * bills/expenses itself, it only renders these already-final numbers
 * (chart data included: every series arrives pre-aggregated and pre-sorted).
 */
export interface BackendDashboardResponse {
  kpis: BackendDashboardKpis;
  operations: BackendDashboardOperations;
  financial: BackendDashboardFinancial;
  recent_activity: BackendDashboardActivityItem[];
  alerts: BackendDashboardAlert[];
  charts: BackendDashboardCharts;
  widgets: BackendDashboardWidgets;
}

/** The client-facing, camelCase shape `dashboard-service.ts` returns. */
export interface DashboardKpis {
  todaysSales: string;
  monthlySales: string;
  customerPaymentsToday: string;
  supplierPaymentsToday: string;
  activeTrips: number;
  boatsAtSea: number;
  todaysCatchQuantity: string;
  draftInvoices: number;
  draftPayments: number;
}

export interface DashboardOperations {
  tripsToday: number;
  tripsActive: number;
  tripsCompletedToday: number;
  boatsAvailable: number;
  boatsAtSea: number;
  boatsMaintenance: number;
}

export interface DashboardFinancial {
  customerOutstanding: string;
  supplierOutstanding: string;
  invoicesIssuedThisMonth: number;
  purchaseBillsThisMonth: number;
}

export interface DashboardActivityItem {
  type: DashboardActivityType;
  reference: string;
  title: string;
  createdAt: string;
}

export interface DashboardAlert {
  type: DashboardAlertType;
  count: number;
  message: string;
}

export interface MonthlySalesPoint {
  month: string;
  salesAmount: string;
  invoiceCount: number;
}

export interface MonthlyPurchasesPoint {
  month: string;
  purchaseAmount: string;
  purchaseBillCount: number;
}

export interface FishSalesPoint {
  fishName: string;
  quantitySold: string;
  salesAmount: string;
}

export interface DashboardTripStatusPoint {
  status: DashboardTripStatusLabel;
  count: number;
}

export interface DashboardCharts {
  monthlySales: MonthlySalesPoint[];
  monthlyPurchases: MonthlyPurchasesPoint[];
  fishSales: FishSalesPoint[];
  tripStatus: DashboardTripStatusPoint[];
}

export interface TopCustomerWidgetItem {
  companyId: string;
  companyName: string;
  totalSales: string;
  invoiceCount: number;
  outstandingAmount: string;
}

export interface TopSupplierWidgetItem {
  supplierId: string;
  supplierName: string;
  purchaseTotal: string;
  purchaseBillCount: number;
  outstandingAmount: string;
}

export interface TopFishWidgetItem {
  fishId: string;
  fishName: string;
  quantitySold: string;
  salesAmount: string;
}

export interface OutstandingSummary {
  customerOutstanding: string;
  customerOverdue: string;
  supplierOutstanding: string;
  supplierOverdue: string;
}

export interface DashboardWidgets {
  topCustomers: TopCustomerWidgetItem[];
  topSuppliers: TopSupplierWidgetItem[];
  topFish: TopFishWidgetItem[];
  outstandingSummary: OutstandingSummary;
}

export interface DashboardData {
  kpis: DashboardKpis;
  operations: DashboardOperations;
  financial: DashboardFinancial;
  recentActivity: DashboardActivityItem[];
  alerts: DashboardAlert[];
  charts: DashboardCharts;
  widgets: DashboardWidgets;
}

export function mapBackendDashboard(payload: BackendDashboardResponse): DashboardData {
  return {
    kpis: {
      todaysSales: payload.kpis.todays_sales,
      monthlySales: payload.kpis.monthly_sales,
      customerPaymentsToday: payload.kpis.customer_payments_today,
      supplierPaymentsToday: payload.kpis.supplier_payments_today,
      activeTrips: payload.kpis.active_trips,
      boatsAtSea: payload.kpis.boats_at_sea,
      todaysCatchQuantity: payload.kpis.todays_catch_quantity,
      draftInvoices: payload.kpis.draft_invoices,
      draftPayments: payload.kpis.draft_payments,
    },
    operations: {
      tripsToday: payload.operations.trips_today,
      tripsActive: payload.operations.trips_active,
      tripsCompletedToday: payload.operations.trips_completed_today,
      boatsAvailable: payload.operations.boats_available,
      boatsAtSea: payload.operations.boats_at_sea,
      boatsMaintenance: payload.operations.boats_maintenance,
    },
    financial: {
      customerOutstanding: payload.financial.customer_outstanding,
      supplierOutstanding: payload.financial.supplier_outstanding,
      invoicesIssuedThisMonth: payload.financial.invoices_issued_this_month,
      purchaseBillsThisMonth: payload.financial.purchase_bills_this_month,
    },
    recentActivity: payload.recent_activity.map((item) => ({
      type: item.type,
      reference: item.reference,
      title: item.title,
      createdAt: item.created_at,
    })),
    alerts: payload.alerts.map((alert) => ({
      type: alert.type,
      count: alert.count,
      message: alert.message,
    })),
    charts: {
      monthlySales: payload.charts.monthly_sales.map((point) => ({
        month: point.month,
        salesAmount: point.sales_amount,
        invoiceCount: point.invoice_count,
      })),
      monthlyPurchases: payload.charts.monthly_purchases.map((point) => ({
        month: point.month,
        purchaseAmount: point.purchase_amount,
        purchaseBillCount: point.purchase_bill_count,
      })),
      fishSales: payload.charts.fish_sales.map((point) => ({
        fishName: point.fish_name,
        quantitySold: point.quantity_sold,
        salesAmount: point.sales_amount,
      })),
      tripStatus: payload.charts.trip_status.map((point) => ({
        status: point.status,
        count: point.count,
      })),
    },
    widgets: {
      topCustomers: payload.widgets.top_customers.map((item) => ({
        companyId: item.company_id,
        companyName: item.company_name,
        totalSales: item.total_sales,
        invoiceCount: item.invoice_count,
        outstandingAmount: item.outstanding_amount,
      })),
      topSuppliers: payload.widgets.top_suppliers.map((item) => ({
        supplierId: item.supplier_id,
        supplierName: item.supplier_name,
        purchaseTotal: item.purchase_total,
        purchaseBillCount: item.purchase_bill_count,
        outstandingAmount: item.outstanding_amount,
      })),
      topFish: payload.widgets.top_fish.map((item) => ({
        fishId: item.fish_id,
        fishName: item.fish_name,
        quantitySold: item.quantity_sold,
        salesAmount: item.sales_amount,
      })),
      outstandingSummary: {
        customerOutstanding: payload.widgets.outstanding_summary.customer_outstanding,
        customerOverdue: payload.widgets.outstanding_summary.customer_overdue,
        supplierOutstanding: payload.widgets.outstanding_summary.supplier_outstanding,
        supplierOverdue: payload.widgets.outstanding_summary.supplier_overdue,
      },
    },
  };
}
