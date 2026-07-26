import { bffClient } from "@/lib/bff-client";
import type { ApiListEnvelope } from "@/types/api";
import type {
  BackendFish,
  Fish,
  FishCreateRequest,
  FishListParams,
  FishUpdateRequest,
} from "@/features/fish/types/fish";
import { mapBackendFish } from "@/features/fish/types/fish";

export interface FishListResult {
  data: Fish[];
  meta: ApiListEnvelope<BackendFish>["meta"];
}

function buildQueryString(params: FishListParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.category) query.set("category", params.category);
  if (params.unit) query.set("unit", params.unit);
  if (params.is_active !== undefined) query.set("is_active", String(params.is_active));
  query.set("sort", params.sort);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/fish/*`) — never the
 * FastAPI backend directly, for the same reason `company-service.ts`
 * doesn't: the browser never holds a bearer token to attach here
 * (ARCHITECTURE.md §1.2, §8.1). The BFF route handlers (`app/api/fish/**`)
 * attach the caller's HttpOnly access token server-side and forward the
 * request.
 */
export const fishService = {
  async listFish(params: FishListParams): Promise<FishListResult> {
    const { data } = await bffClient.get<ApiListEnvelope<BackendFish>>(`/fish?${buildQueryString(params)}`);
    return { data: data.data.map(mapBackendFish), meta: data.meta };
  },

  async getFish(id: string): Promise<Fish> {
    const { data } = await bffClient.get<BackendFish>(`/fish/${id}`);
    return mapBackendFish(data);
  },

  async createFish(payload: FishCreateRequest): Promise<Fish> {
    const { data } = await bffClient.post<BackendFish>("/fish", payload);
    return mapBackendFish(data);
  },

  async updateFish(id: string, payload: FishUpdateRequest): Promise<Fish> {
    const { data } = await bffClient.put<BackendFish>(`/fish/${id}`, payload);
    return mapBackendFish(data);
  },

  async deleteFish(id: string): Promise<void> {
    await bffClient.delete(`/fish/${id}`);
  },
};
