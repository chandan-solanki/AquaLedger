import type { ProfitabilityFilter } from "@/features/reports/constants/profitability";

/** Mirrors the backend's TripStatus enum (app/modules/trips/constants.py). Always "returned" in this report's rows - a hard invariant, not a value that varies. */
export type TripProfitabilityStatus = "planned" | "departed" | "returned" | "cancelled";

/**
 * Raw backend shape (snake_case), matching TripProfitabilityResponse
 * (app/modules/reports/schemas.py) exactly. Every money field is a string -
 * the backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1).
 */
export interface BackendTripProfitabilityRow {
  trip_id: string;
  trip_number: string;
  boat_id: string;
  boat_name: string;
  departure_date: string;
  return_date: string | null;
  status: TripProfitabilityStatus;
  revenue: string;
  expenses: string;
  profit: string;
  profit_margin_percent: string;
}

export interface BackendTripProfitabilitySummary {
  total_revenue: string;
  total_expenses: string;
  total_profit: string;
  average_profit_per_trip: string;
  average_revenue_per_trip: string;
  most_profitable_trip_number: string | null;
  most_profitable_trip_profit: string | null;
  loss_making_trips: number;
}

export interface BackendPaginationMeta {
  total_records: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface BackendTripProfitabilityResponse {
  summary: BackendTripProfitabilitySummary;
  rows: BackendTripProfitabilityRow[];
  pagination: BackendPaginationMeta;
}

/** The client-facing, camelCase shape reportsService.getTripProfitability returns. */
export interface TripProfitabilityRow {
  tripId: string;
  tripNumber: string;
  boatId: string;
  boatName: string;
  departureDate: string;
  returnDate: string | null;
  status: TripProfitabilityStatus;
  revenue: string;
  expenses: string;
  profit: string;
  profitMarginPercent: string;
}

export interface TripProfitabilitySummary {
  totalRevenue: string;
  totalExpenses: string;
  totalProfit: string;
  averageProfitPerTrip: string;
  averageRevenuePerTrip: string;
  mostProfitableTripNumber: string | null;
  mostProfitableTripProfit: string | null;
  lossMakingTrips: number;
}

export interface PaginationMeta {
  totalRecords: number;
  totalPages: number;
  currentPage: number;
  pageSize: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface TripProfitabilityData {
  summary: TripProfitabilitySummary;
  rows: TripProfitabilityRow[];
  pagination: PaginationMeta;
}

export function mapBackendTripProfitability(
  response: BackendTripProfitabilityResponse
): TripProfitabilityData {
  return {
    summary: {
      totalRevenue: response.summary.total_revenue,
      totalExpenses: response.summary.total_expenses,
      totalProfit: response.summary.total_profit,
      averageProfitPerTrip: response.summary.average_profit_per_trip,
      averageRevenuePerTrip: response.summary.average_revenue_per_trip,
      mostProfitableTripNumber: response.summary.most_profitable_trip_number,
      mostProfitableTripProfit: response.summary.most_profitable_trip_profit,
      lossMakingTrips: response.summary.loss_making_trips,
    },
    rows: response.rows.map((row) => ({
      tripId: row.trip_id,
      tripNumber: row.trip_number,
      boatId: row.boat_id,
      boatName: row.boat_name,
      departureDate: row.departure_date,
      returnDate: row.return_date,
      status: row.status,
      revenue: row.revenue,
      expenses: row.expenses,
      profit: row.profit,
      profitMarginPercent: row.profit_margin_percent,
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
 * Query params for GET /reports/trip-profitability
 * (app/modules/reports/schemas.py's TripProfitabilityParams) - snake_case to
 * match the wire format exactly. No `status` field - only `returned` trips
 * are ever eligible (a hard backend invariant), so a status filter would be
 * a no-op. No `sort` field - the backend's order is fixed (`return date
 * DESC, trip number DESC`), not client-configurable.
 */
export interface TripProfitabilityParams {
  boat_id?: string;
  from_date?: string;
  to_date?: string;
  profitability?: ProfitabilityFilter;
  q?: string;
  page: number;
  page_size: number;
}
