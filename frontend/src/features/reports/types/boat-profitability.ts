import type { ProfitabilityFilter } from "@/features/reports/constants/profitability";

/**
 * Raw backend shape (snake_case), matching BoatProfitabilityResponse
 * (app/modules/reports/schemas.py) exactly. Every money field is a string -
 * the backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1).
 */
export interface BackendBoatProfitabilityRow {
  boat_id: string;
  boat_name: string;
  registration_number: string;
  total_trips: number;
  revenue: string;
  expenses: string;
  profit: string;
  profit_margin_percent: string;
  average_profit_per_trip: string;
  average_revenue_per_trip: string;
  best_trip_profit: string;
  worst_trip_profit: string;
  last_trip_date: string | null;
}

export interface BackendBoatProfitabilitySummary {
  fleet_revenue: string;
  fleet_expenses: string;
  fleet_profit: string;
  fleet_margin_percent: string;
  total_boats: number;
  active_boats: number;
  average_profit_per_boat: string;
  most_profitable_boat_name: string | null;
  most_profitable_boat_profit: string | null;
}

export interface BackendPaginationMeta {
  total_records: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface BackendBoatProfitabilityResponse {
  summary: BackendBoatProfitabilitySummary;
  rows: BackendBoatProfitabilityRow[];
  pagination: BackendPaginationMeta;
}

/** The client-facing, camelCase shape reportsService.getBoatProfitability returns. */
export interface BoatProfitabilityRow {
  boatId: string;
  boatName: string;
  registrationNumber: string;
  totalTrips: number;
  revenue: string;
  expenses: string;
  profit: string;
  profitMarginPercent: string;
  averageProfitPerTrip: string;
  averageRevenuePerTrip: string;
  bestTripProfit: string;
  worstTripProfit: string;
  lastTripDate: string | null;
}

export interface BoatProfitabilitySummary {
  fleetRevenue: string;
  fleetExpenses: string;
  fleetProfit: string;
  fleetMarginPercent: string;
  totalBoats: number;
  activeBoats: number;
  averageProfitPerBoat: string;
  mostProfitableBoatName: string | null;
  mostProfitableBoatProfit: string | null;
}

export interface PaginationMeta {
  totalRecords: number;
  totalPages: number;
  currentPage: number;
  pageSize: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface BoatProfitabilityData {
  summary: BoatProfitabilitySummary;
  rows: BoatProfitabilityRow[];
  pagination: PaginationMeta;
}

export function mapBackendBoatProfitability(
  response: BackendBoatProfitabilityResponse
): BoatProfitabilityData {
  return {
    summary: {
      fleetRevenue: response.summary.fleet_revenue,
      fleetExpenses: response.summary.fleet_expenses,
      fleetProfit: response.summary.fleet_profit,
      fleetMarginPercent: response.summary.fleet_margin_percent,
      totalBoats: response.summary.total_boats,
      activeBoats: response.summary.active_boats,
      averageProfitPerBoat: response.summary.average_profit_per_boat,
      mostProfitableBoatName: response.summary.most_profitable_boat_name,
      mostProfitableBoatProfit: response.summary.most_profitable_boat_profit,
    },
    rows: response.rows.map((row) => ({
      boatId: row.boat_id,
      boatName: row.boat_name,
      registrationNumber: row.registration_number,
      totalTrips: row.total_trips,
      revenue: row.revenue,
      expenses: row.expenses,
      profit: row.profit,
      profitMarginPercent: row.profit_margin_percent,
      averageProfitPerTrip: row.average_profit_per_trip,
      averageRevenuePerTrip: row.average_revenue_per_trip,
      bestTripProfit: row.best_trip_profit,
      worstTripProfit: row.worst_trip_profit,
      lastTripDate: row.last_trip_date,
    })),
    pagination: {
      totalRecords: response.pagination.total_records,
      totalPages: response.pagination.total_pages,
      currentPage: response.pagination.current_page,
      pageSize: response.pagination.page_size,
      hasNext: response.pagination.has_next,
      hasPrevious: response.pagination.has_previous,
    },
  };
}

/**
 * Query params for GET /reports/boat-profitability
 * (app/modules/reports/schemas.py's BoatProfitabilityParams) - snake_case to
 * match the wire format exactly. `boat_id` narrows to a single boat - used
 * by the Boat Detail page's own Profitability tab to fetch that boat's
 * Lifetime Summary. No `sort` field - the backend's order is fixed
 * (`profit DESC, boat name ASC`), not client-configurable.
 */
export interface BoatProfitabilityParams {
  boat_id?: string;
  from_date?: string;
  to_date?: string;
  min_trips?: number;
  profitability?: ProfitabilityFilter;
  q?: string;
  page: number;
  page_size: number;
}
