import { bffClient } from "@/lib/bff-client";
import type { ApiListEnvelope } from "@/types/api";
import type {
  BackendTrip,
  Trip,
  TripCreateRequest,
  TripListParams,
  TripUpdateRequest,
} from "@/features/trips/types/trip";
import { mapBackendTrip } from "@/features/trips/types/trip";

export interface TripListResult {
  data: Trip[];
  meta: ApiListEnvelope<BackendTrip>["meta"];
}

function buildQueryString(params: TripListParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.boat_id) query.set("boat_id", params.boat_id);
  if (params.status) query.set("status", params.status);
  if (params.trip_type) query.set("trip_type", params.trip_type);
  if (params.departure_date_from) query.set("departure_date_from", params.departure_date_from);
  if (params.departure_date_to) query.set("departure_date_to", params.departure_date_to);
  if (params.return_date_from) query.set("return_date_from", params.return_date_from);
  if (params.return_date_to) query.set("return_date_to", params.return_date_to);
  query.set("sort", params.sort);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/trips/*`) — never the
 * FastAPI backend directly, mirroring `boat-service.ts`: the browser never
 * holds a bearer token to attach here (ARCHITECTURE.md §1.2, §8.1). The BFF
 * route handlers (`app/api/trips/**`) attach the caller's HttpOnly access
 * token server-side and forward the request.
 */
export const tripService = {
  async listTrips(params: TripListParams): Promise<TripListResult> {
    const { data } = await bffClient.get<ApiListEnvelope<BackendTrip>>(`/trips?${buildQueryString(params)}`);
    return { data: data.data.map(mapBackendTrip), meta: data.meta };
  },

  async getTrip(id: string): Promise<Trip> {
    const { data } = await bffClient.get<BackendTrip>(`/trips/${id}`);
    return mapBackendTrip(data);
  },

  async createTrip(payload: TripCreateRequest): Promise<Trip> {
    const { data } = await bffClient.post<BackendTrip>("/trips", payload);
    return mapBackendTrip(data);
  },

  async updateTrip(id: string, payload: TripUpdateRequest): Promise<Trip> {
    const { data } = await bffClient.put<BackendTrip>(`/trips/${id}`, payload);
    return mapBackendTrip(data);
  },

  async deleteTrip(id: string): Promise<void> {
    await bffClient.delete(`/trips/${id}`);
  },
};
