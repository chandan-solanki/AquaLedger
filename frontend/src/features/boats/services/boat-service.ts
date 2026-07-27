import { bffClient } from "@/lib/bff-client";
import type { ApiListEnvelope } from "@/types/api";
import type {
  BackendBoat,
  Boat,
  BoatCreateRequest,
  BoatListParams,
  BoatUpdateRequest,
} from "@/features/boats/types/boat";
import { mapBackendBoat } from "@/features/boats/types/boat";

export interface BoatListResult {
  data: Boat[];
  meta: ApiListEnvelope<BackendBoat>["meta"];
}

function buildQueryString(params: BoatListParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.boat_type) query.set("boat_type", params.boat_type);
  if (params.is_active !== undefined) query.set("is_active", String(params.is_active));
  if (params.insurance_expired !== undefined)
    query.set("insurance_expired", String(params.insurance_expired));
  if (params.license_expired !== undefined)
    query.set("license_expired", String(params.license_expired));
  query.set("sort", params.sort);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/boats/*`) — never the
 * FastAPI backend directly, for the same reason `fish-service.ts` doesn't:
 * the browser never holds a bearer token to attach here (ARCHITECTURE.md
 * §1.2, §8.1). The BFF route handlers (`app/api/boats/**`) attach the
 * caller's HttpOnly access token server-side and forward the request.
 */
export const boatService = {
  async listBoats(params: BoatListParams): Promise<BoatListResult> {
    const { data } = await bffClient.get<ApiListEnvelope<BackendBoat>>(`/boats?${buildQueryString(params)}`);
    return { data: data.data.map(mapBackendBoat), meta: data.meta };
  },

  async getBoat(id: string): Promise<Boat> {
    const { data } = await bffClient.get<BackendBoat>(`/boats/${id}`);
    return mapBackendBoat(data);
  },

  async createBoat(payload: BoatCreateRequest): Promise<Boat> {
    const { data } = await bffClient.post<BackendBoat>("/boats", payload);
    return mapBackendBoat(data);
  },

  async updateBoat(id: string, payload: BoatUpdateRequest): Promise<Boat> {
    const { data } = await bffClient.put<BackendBoat>(`/boats/${id}`, payload);
    return mapBackendBoat(data);
  },

  async deleteBoat(id: string): Promise<void> {
    await bffClient.delete(`/boats/${id}`);
  },
};
