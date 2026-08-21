import { bffClient } from "@/lib/bff-client";
import type { ApiListEnvelope } from "@/types/api";
import type {
  BackendFishStockDetail,
  BackendFishStockRow,
  FishStockDetail,
  FishStockListParams,
  FishStockRow,
} from "@/features/fish-stock/types/fish-stock";
import { mapBackendFishStockDetail, mapBackendFishStockRow } from "@/features/fish-stock/types/fish-stock";

export interface FishStockListResult {
  data: FishStockRow[];
  meta: ApiListEnvelope<BackendFishStockRow>["meta"];
}

function buildQueryString(params: FishStockListParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.is_active !== undefined) query.set("is_active", String(params.is_active));
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/fish-stock/*`) — never
 * the FastAPI backend directly, the same reason every other `*-service.ts`
 * in this app does (the browser never holds a bearer token to attach here,
 * ARCHITECTURE.md §1.2, §8.1). The BFF route handlers (`app/api/fish-stock/**`)
 * attach the caller's HttpOnly access token server-side and forward the
 * request to the read-only GET /api/v1/fish-stock endpoints built in
 * Sprint 15 Session 2.
 */
export const fishStockService = {
  async listFishStock(params: FishStockListParams): Promise<FishStockListResult> {
    const { data } = await bffClient.get<ApiListEnvelope<BackendFishStockRow>>(
      `/fish-stock?${buildQueryString(params)}`
    );
    return { data: data.data.map(mapBackendFishStockRow), meta: data.meta };
  },

  async getFishStockDetail(fishId: string): Promise<FishStockDetail> {
    const { data } = await bffClient.get<BackendFishStockDetail>(`/fish-stock/${fishId}`);
    return mapBackendFishStockDetail(data);
  },
};
