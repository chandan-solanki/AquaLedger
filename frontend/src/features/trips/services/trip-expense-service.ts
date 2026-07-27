import { bffClient } from "@/lib/bff-client";
import type { ApiListEnvelope } from "@/types/api";
import type {
  BackendTripExpense,
  TripExpense,
  TripExpenseCreateRequest,
  TripExpenseListParams,
  TripExpenseUpdateRequest,
} from "@/features/trips/types/trip-expense";
import { mapBackendTripExpense } from "@/features/trips/types/trip-expense";

export interface TripExpenseListResult {
  data: TripExpense[];
  meta: ApiListEnvelope<BackendTripExpense>["meta"];
}

function buildQueryString(params: TripExpenseListParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.trip_id) query.set("trip_id", params.trip_id);
  if (params.expense_type) query.set("expense_type", params.expense_type);
  if (params.expense_date_from) query.set("expense_date_from", params.expense_date_from);
  if (params.expense_date_to) query.set("expense_date_to", params.expense_date_to);
  if (params.sort) query.set("sort", params.sort);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/trip-expenses`) — never
 * the FastAPI backend directly, mirroring `trip-service.ts`: the browser
 * never holds a bearer token to attach here (ARCHITECTURE.md §1.2, §8.1).
 * `trip-expenses` is a separate top-level backend resource
 * (app/modules/trip_expenses/router.py, prefix `/trip-expenses`) filtered
 * by `trip_id` — it is not nested under `/trips/{id}` and not embedded in
 * `TripResponse`, so this module queries it independently rather than
 * assuming it comes back with the trip.
 */
export const tripExpenseService = {
  async listTripExpenses(params: TripExpenseListParams): Promise<TripExpenseListResult> {
    const { data } = await bffClient.get<ApiListEnvelope<BackendTripExpense>>(
      `/trip-expenses?${buildQueryString(params)}`
    );
    return { data: data.data.map(mapBackendTripExpense), meta: data.meta };
  },

  async getTripExpense(id: string): Promise<TripExpense> {
    const { data } = await bffClient.get<BackendTripExpense>(`/trip-expenses/${id}`);
    return mapBackendTripExpense(data);
  },

  async createTripExpense(payload: TripExpenseCreateRequest): Promise<TripExpense> {
    const { data } = await bffClient.post<BackendTripExpense>("/trip-expenses", payload);
    return mapBackendTripExpense(data);
  },

  async updateTripExpense(id: string, payload: TripExpenseUpdateRequest): Promise<TripExpense> {
    const { data } = await bffClient.put<BackendTripExpense>(`/trip-expenses/${id}`, payload);
    return mapBackendTripExpense(data);
  },

  async deleteTripExpense(id: string): Promise<void> {
    await bffClient.delete(`/trip-expenses/${id}`);
  },
};
