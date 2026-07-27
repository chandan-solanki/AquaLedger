import { bffClient } from "@/lib/bff-client";
import type { ApiListEnvelope } from "@/types/api";
import type {
  BackendTripCatch,
  TripCatch,
  TripCatchCreateRequest,
  TripCatchListParams,
  TripCatchUpdateRequest,
} from "@/features/trips/types/trip-catch";
import { mapBackendTripCatch } from "@/features/trips/types/trip-catch";

export interface TripCatchListResult {
  data: TripCatch[];
  meta: ApiListEnvelope<BackendTripCatch>["meta"];
}

function buildQueryString(params: TripCatchListParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.trip_id) query.set("trip_id", params.trip_id);
  if (params.fish_id) query.set("fish_id", params.fish_id);
  if (params.grade) query.set("grade", params.grade);
  if (params.landing_date_from) query.set("landing_date_from", params.landing_date_from);
  if (params.landing_date_to) query.set("landing_date_to", params.landing_date_to);
  if (params.sort) query.set("sort", params.sort);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/trip-catches`) — never
 * the FastAPI backend directly, mirroring `trip-service.ts`: the browser
 * never holds a bearer token to attach here (ARCHITECTURE.md §1.2, §8.1).
 * `trip-catches` is a separate top-level backend resource
 * (app/modules/trip_catches/router.py, prefix `/trip-catches`) filtered by
 * `trip_id` — it is not nested under `/trips/{id}` and not embedded in
 * `TripResponse`, so this module queries it independently rather than
 * assuming it comes back with the trip.
 */
export const tripCatchService = {
  async listTripCatches(params: TripCatchListParams): Promise<TripCatchListResult> {
    const { data } = await bffClient.get<ApiListEnvelope<BackendTripCatch>>(
      `/trip-catches?${buildQueryString(params)}`
    );
    return { data: data.data.map(mapBackendTripCatch), meta: data.meta };
  },

  async getTripCatch(id: string): Promise<TripCatch> {
    const { data } = await bffClient.get<BackendTripCatch>(`/trip-catches/${id}`);
    return mapBackendTripCatch(data);
  },

  async createTripCatch(payload: TripCatchCreateRequest): Promise<TripCatch> {
    const { data } = await bffClient.post<BackendTripCatch>("/trip-catches", payload);
    return mapBackendTripCatch(data);
  },

  async updateTripCatch(id: string, payload: TripCatchUpdateRequest): Promise<TripCatch> {
    const { data } = await bffClient.put<BackendTripCatch>(`/trip-catches/${id}`, payload);
    return mapBackendTripCatch(data);
  },

  async deleteTripCatch(id: string): Promise<void> {
    await bffClient.delete(`/trip-catches/${id}`);
  },
};
