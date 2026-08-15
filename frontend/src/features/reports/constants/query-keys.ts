import type { CustomerLedgerParams } from "@/features/reports/types/customer-ledger";
import type { SalesReportParams } from "@/features/reports/types/sales-report";
import type { PurchaseReportParams } from "@/features/reports/types/purchase-report";
import type { OutstandingReportParams } from "@/features/reports/types/outstanding-report";
import type { AgingReportParams } from "@/features/reports/types/aging-report";
import type { SupplierLedgerParams } from "@/features/reports/types/supplier-ledger";
import type { TripProfitabilityParams } from "@/features/reports/types/trip-profitability";
import type { BoatProfitabilityParams } from "@/features/reports/types/boat-profitability";
import type { FishSalesParams } from "@/features/reports/types/fish-sales";
import type { FishSalesHistoryParams } from "@/features/reports/types/fish-sales-history";

export const reportKeys = {
  all: () => ["reports"] as const,
  customerLedger: () => [...reportKeys.all(), "customer-ledger"] as const,
  customerLedgerResult: (params: CustomerLedgerParams) =>
    [...reportKeys.customerLedger(), params] as const,
  supplierLedger: () => [...reportKeys.all(), "supplier-ledger"] as const,
  supplierLedgerResult: (params: SupplierLedgerParams) =>
    [...reportKeys.supplierLedger(), params] as const,
  salesReport: () => [...reportKeys.all(), "sales"] as const,
  salesReportResult: (params: SalesReportParams) => [...reportKeys.salesReport(), params] as const,
  purchaseReport: () => [...reportKeys.all(), "purchases"] as const,
  purchaseReportResult: (params: PurchaseReportParams) =>
    [...reportKeys.purchaseReport(), params] as const,
  outstandingReport: () => [...reportKeys.all(), "outstanding"] as const,
  outstandingReportResult: (params: OutstandingReportParams) =>
    [...reportKeys.outstandingReport(), params] as const,
  agingReport: () => [...reportKeys.all(), "aging"] as const,
  agingReportResult: (params: AgingReportParams) =>
    [...reportKeys.agingReport(), params] as const,
  tripProfitability: () => [...reportKeys.all(), "trip-profitability"] as const,
  tripProfitabilityResult: (params: TripProfitabilityParams) =>
    [...reportKeys.tripProfitability(), params] as const,
  boatProfitability: () => [...reportKeys.all(), "boat-profitability"] as const,
  boatProfitabilityResult: (params: BoatProfitabilityParams) =>
    [...reportKeys.boatProfitability(), params] as const,
  fishSales: () => [...reportKeys.all(), "fish-sales"] as const,
  fishSalesResult: (params: FishSalesParams) => [...reportKeys.fishSales(), params] as const,
  fishSalesHistory: () => [...reportKeys.all(), "fish-sales-history"] as const,
  fishSalesHistoryResult: (params: FishSalesHistoryParams) =>
    [...reportKeys.fishSalesHistory(), params] as const,
};
