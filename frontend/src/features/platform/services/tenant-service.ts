import { bffClient } from "@/lib/bff-client";
import type { ApiListEnvelope } from "@/types/api";
import type {
  BackendTenant,
  BackendTenantProvisioningResponse,
  Tenant,
  TenantCreateRequest,
  TenantListParams,
  TenantProvisioningResult,
  TenantStatus,
} from "@/features/platform/types/tenant";
import { mapBackendTenant, mapBackendTenantProvisioningResponse } from "@/features/platform/types/tenant";

export interface TenantListResult {
  data: Tenant[];
  meta: ApiListEnvelope<BackendTenant>["meta"];
}

function buildQueryString(params: TenantListParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.status) query.set("status", params.status);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/platform/tenants/*`) —
 * never the FastAPI backend directly, same rationale as every other
 * *-service.ts in this codebase (the browser never holds a bearer token).
 * The BFF route handlers (`app/api/platform/tenants/**`) attach the caller's
 * HttpOnly access token server-side and forward the request; the real
 * `require_platform_admin` check happens only on the FastAPI side.
 */
export const platformTenantService = {
  async listTenants(params: TenantListParams): Promise<TenantListResult> {
    const { data } = await bffClient.get<ApiListEnvelope<BackendTenant>>(
      `/platform/tenants?${buildQueryString(params)}`
    );
    return { data: data.data.map(mapBackendTenant), meta: data.meta };
  },

  async getTenant(id: string): Promise<Tenant> {
    const { data } = await bffClient.get<BackendTenant>(`/platform/tenants/${id}`);
    return mapBackendTenant(data);
  },

  async createTenant(payload: TenantCreateRequest): Promise<TenantProvisioningResult> {
    const { data } = await bffClient.post<BackendTenantProvisioningResponse>(
      "/platform/tenants",
      payload
    );
    return mapBackendTenantProvisioningResponse(data);
  },

  async updateTenantStatus(id: string, status: TenantStatus): Promise<Tenant> {
    const { data } = await bffClient.patch<BackendTenant>(`/platform/tenants/${id}/status`, { status });
    return mapBackendTenant(data);
  },
};
