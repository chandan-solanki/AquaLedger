import { bffClient } from "@/lib/bff-client";
import type { ApiListEnvelope } from "@/types/api";
import type {
  BackendSupplier,
  Supplier,
  SupplierCreateRequest,
  SupplierListParams,
  SupplierUpdateRequest,
} from "@/features/suppliers/types/supplier";
import { mapBackendSupplier } from "@/features/suppliers/types/supplier";

export interface SupplierListResult {
  data: Supplier[];
  meta: ApiListEnvelope<BackendSupplier>["meta"];
}

function buildQueryString(params: SupplierListParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.status) query.set("status", params.status);
  if (params.city) query.set("city", params.city);
  if (params.state) query.set("state", params.state);
  query.set("sort", params.sort);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/suppliers/*`) - never
 * the FastAPI backend directly, mirroring `company-service.ts`: the browser
 * never holds a bearer token to attach here (ARCHITECTURE.md §1.2, §8.1).
 * The BFF route handlers (`app/api/suppliers/**`) attach the caller's
 * HttpOnly access token server-side and forward the request.
 */
export const supplierService = {
  async listSuppliers(params: SupplierListParams): Promise<SupplierListResult> {
    const { data } = await bffClient.get<ApiListEnvelope<BackendSupplier>>(
      `/suppliers?${buildQueryString(params)}`
    );
    return { data: data.data.map(mapBackendSupplier), meta: data.meta };
  },

  async getSupplier(id: string): Promise<Supplier> {
    const { data } = await bffClient.get<BackendSupplier>(`/suppliers/${id}`);
    return mapBackendSupplier(data);
  },

  async createSupplier(payload: SupplierCreateRequest): Promise<Supplier> {
    const { data } = await bffClient.post<BackendSupplier>("/suppliers", payload);
    return mapBackendSupplier(data);
  },

  async updateSupplier(id: string, payload: SupplierUpdateRequest): Promise<Supplier> {
    const { data } = await bffClient.put<BackendSupplier>(`/suppliers/${id}`, payload);
    return mapBackendSupplier(data);
  },

  async deleteSupplier(id: string): Promise<void> {
    await bffClient.delete(`/suppliers/${id}`);
  },
};
