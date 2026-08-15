import { bffClient } from "@/lib/bff-client";
import type {
  BackendCustomerLedgerResponse,
  CustomerLedgerData,
  CustomerLedgerParams,
} from "@/features/reports/types/customer-ledger";
import { mapBackendCustomerLedger } from "@/features/reports/types/customer-ledger";
import type {
  BackendSupplierLedgerResponse,
  SupplierLedgerData,
  SupplierLedgerParams,
} from "@/features/reports/types/supplier-ledger";
import { mapBackendSupplierLedger } from "@/features/reports/types/supplier-ledger";
import type {
  BackendSalesReportResponse,
  SalesReportData,
  SalesReportParams,
} from "@/features/reports/types/sales-report";
import { mapBackendSalesReport } from "@/features/reports/types/sales-report";
import type {
  BackendPurchaseReportResponse,
  PurchaseReportData,
  PurchaseReportParams,
} from "@/features/reports/types/purchase-report";
import { mapBackendPurchaseReport } from "@/features/reports/types/purchase-report";
import type {
  BackendOutstandingReportResponse,
  OutstandingReportData,
  OutstandingReportParams,
} from "@/features/reports/types/outstanding-report";
import { mapBackendOutstandingReport } from "@/features/reports/types/outstanding-report";
import type {
  BackendAgingReportResponse,
  AgingReportData,
  AgingReportParams,
} from "@/features/reports/types/aging-report";
import { mapBackendAgingReport } from "@/features/reports/types/aging-report";
import type {
  BackendTripProfitabilityResponse,
  TripProfitabilityData,
  TripProfitabilityParams,
} from "@/features/reports/types/trip-profitability";
import { mapBackendTripProfitability } from "@/features/reports/types/trip-profitability";
import type {
  BackendBoatProfitabilityResponse,
  BoatProfitabilityData,
  BoatProfitabilityParams,
} from "@/features/reports/types/boat-profitability";
import { mapBackendBoatProfitability } from "@/features/reports/types/boat-profitability";
import type {
  BackendFishSalesResponse,
  FishSalesData,
  FishSalesParams,
} from "@/features/reports/types/fish-sales";
import { mapBackendFishSales } from "@/features/reports/types/fish-sales";
import type {
  BackendFishSalesHistoryResponse,
  FishSalesHistoryData,
  FishSalesHistoryParams,
} from "@/features/reports/types/fish-sales-history";
import { mapBackendFishSalesHistory } from "@/features/reports/types/fish-sales-history";

function buildQueryString(params: CustomerLedgerParams): string {
  const query = new URLSearchParams();
  query.set("customer_id", params.customer_id);
  if (params.from_date) query.set("from_date", params.from_date);
  if (params.to_date) query.set("to_date", params.to_date);
  if (params.transaction_type) query.set("transaction_type", params.transaction_type);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

function buildSupplierQueryString(params: SupplierLedgerParams): string {
  const query = new URLSearchParams();
  query.set("supplier_id", params.supplier_id);
  if (params.from_date) query.set("from_date", params.from_date);
  if (params.to_date) query.set("to_date", params.to_date);
  if (params.transaction_type) query.set("transaction_type", params.transaction_type);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

function buildSalesReportQueryString(params: SalesReportParams): string {
  const query = new URLSearchParams();
  if (params.customer_id) query.set("customer_id", params.customer_id);
  if (params.from_date) query.set("from_date", params.from_date);
  if (params.to_date) query.set("to_date", params.to_date);
  if (params.status) query.set("status", params.status);
  if (params.paid_status) query.set("paid_status", params.paid_status);
  if (params.q) query.set("q", params.q);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

function buildPurchaseReportQueryString(params: PurchaseReportParams): string {
  const query = new URLSearchParams();
  if (params.supplier_id) query.set("supplier_id", params.supplier_id);
  if (params.from_date) query.set("from_date", params.from_date);
  if (params.to_date) query.set("to_date", params.to_date);
  if (params.status) query.set("status", params.status);
  if (params.paid_status) query.set("paid_status", params.paid_status);
  if (params.q) query.set("q", params.q);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

function buildOutstandingReportQueryString(params: OutstandingReportParams): string {
  const query = new URLSearchParams();
  query.set("entity_type", params.entity_type);
  if (params.outstanding_only) query.set("outstanding_only", "true");
  if (params.overdue_only) query.set("overdue_only", "true");
  if (params.risk_level) query.set("risk_level", params.risk_level);
  if (params.from_date) query.set("from_date", params.from_date);
  if (params.to_date) query.set("to_date", params.to_date);
  if (params.q) query.set("q", params.q);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

function buildAgingReportQueryString(params: AgingReportParams): string {
  const query = new URLSearchParams();
  query.set("entity_type", params.entity_type);
  if (params.outstanding_only) query.set("outstanding_only", "true");
  if (params.risk_level) query.set("risk_level", params.risk_level);
  if (params.q) query.set("q", params.q);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

function buildTripProfitabilityQueryString(params: TripProfitabilityParams): string {
  const query = new URLSearchParams();
  if (params.boat_id) query.set("boat_id", params.boat_id);
  if (params.from_date) query.set("from_date", params.from_date);
  if (params.to_date) query.set("to_date", params.to_date);
  if (params.profitability) query.set("profitability", params.profitability);
  if (params.q) query.set("q", params.q);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

function buildBoatProfitabilityQueryString(params: BoatProfitabilityParams): string {
  const query = new URLSearchParams();
  if (params.boat_id) query.set("boat_id", params.boat_id);
  if (params.from_date) query.set("from_date", params.from_date);
  if (params.to_date) query.set("to_date", params.to_date);
  if (params.min_trips) query.set("min_trips", String(params.min_trips));
  if (params.profitability) query.set("profitability", params.profitability);
  if (params.q) query.set("q", params.q);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

function buildFishSalesQueryString(params: FishSalesParams): string {
  const query = new URLSearchParams();
  if (params.fish_id) query.set("fish_id", params.fish_id);
  if (params.from_date) query.set("from_date", params.from_date);
  if (params.to_date) query.set("to_date", params.to_date);
  if (params.customer_id) query.set("customer_id", params.customer_id);
  if (params.boat_id) query.set("boat_id", params.boat_id);
  if (params.trip_id) query.set("trip_id", params.trip_id);
  if (params.min_quantity) query.set("min_quantity", params.min_quantity);
  if (params.min_revenue) query.set("min_revenue", params.min_revenue);
  if (params.q) query.set("q", params.q);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

function buildFishSalesHistoryQueryString(params: FishSalesHistoryParams): string {
  const query = new URLSearchParams();
  query.set("fish_id", params.fish_id);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/reports/*`) — never the
 * FastAPI backend directly, the same reason every other `*-service.ts` in
 * this app does (the browser never holds a bearer token to attach itself,
 * ARCHITECTURE.md §1.2, §8.1). Each BFF route handler attaches the caller's
 * HttpOnly access token server-side and forwards the request.
 */
export const reportsService = {
  async getCustomerLedger(params: CustomerLedgerParams): Promise<CustomerLedgerData> {
    const { data } = await bffClient.get<BackendCustomerLedgerResponse>(
      `/reports/customer-ledger?${buildQueryString(params)}`
    );
    return mapBackendCustomerLedger(data);
  },

  async getSupplierLedger(params: SupplierLedgerParams): Promise<SupplierLedgerData> {
    const { data } = await bffClient.get<BackendSupplierLedgerResponse>(
      `/reports/supplier-ledger?${buildSupplierQueryString(params)}`
    );
    return mapBackendSupplierLedger(data);
  },

  async getSalesReport(params: SalesReportParams): Promise<SalesReportData> {
    const { data } = await bffClient.get<BackendSalesReportResponse>(
      `/reports/sales?${buildSalesReportQueryString(params)}`
    );
    return mapBackendSalesReport(data);
  },

  async getPurchaseReport(params: PurchaseReportParams): Promise<PurchaseReportData> {
    const { data } = await bffClient.get<BackendPurchaseReportResponse>(
      `/reports/purchases?${buildPurchaseReportQueryString(params)}`
    );
    return mapBackendPurchaseReport(data);
  },

  async getOutstandingReport(params: OutstandingReportParams): Promise<OutstandingReportData> {
    const { data } = await bffClient.get<BackendOutstandingReportResponse>(
      `/reports/outstanding?${buildOutstandingReportQueryString(params)}`
    );
    return mapBackendOutstandingReport(data);
  },

  async getAgingReport(params: AgingReportParams): Promise<AgingReportData> {
    const { data } = await bffClient.get<BackendAgingReportResponse>(
      `/reports/aging?${buildAgingReportQueryString(params)}`
    );
    return mapBackendAgingReport(data);
  },

  async getTripProfitability(params: TripProfitabilityParams): Promise<TripProfitabilityData> {
    const { data } = await bffClient.get<BackendTripProfitabilityResponse>(
      `/reports/trip-profitability?${buildTripProfitabilityQueryString(params)}`
    );
    return mapBackendTripProfitability(data);
  },

  async getBoatProfitability(params: BoatProfitabilityParams): Promise<BoatProfitabilityData> {
    const { data } = await bffClient.get<BackendBoatProfitabilityResponse>(
      `/reports/boat-profitability?${buildBoatProfitabilityQueryString(params)}`
    );
    return mapBackendBoatProfitability(data);
  },

  async getFishSales(params: FishSalesParams): Promise<FishSalesData> {
    const { data } = await bffClient.get<BackendFishSalesResponse>(
      `/reports/fish-sales?${buildFishSalesQueryString(params)}`
    );
    return mapBackendFishSales(data);
  },

  async getFishSalesHistory(params: FishSalesHistoryParams): Promise<FishSalesHistoryData> {
    const { data } = await bffClient.get<BackendFishSalesHistoryResponse>(
      `/reports/fish-sales-history?${buildFishSalesHistoryQueryString(params)}`
    );
    return mapBackendFishSalesHistory(data);
  },
};
