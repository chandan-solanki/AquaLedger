import { bffClient } from "@/lib/bff-client";
import type { ApiListEnvelope } from "@/types/api";
import type {
  BackendCompany,
  Company,
  CompanyCreateRequest,
  CompanyListParams,
  CompanyUpdateRequest,
} from "@/features/companies/types/company";
import { mapBackendCompany } from "@/features/companies/types/company";

export interface CompanyListResult {
  data: Company[];
  meta: ApiListEnvelope<BackendCompany>["meta"];
}

function buildQueryString(params: CompanyListParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.company_type) query.set("company_type", params.company_type);
  if (params.status) query.set("status", params.status);
  if (params.city) query.set("city", params.city);
  if (params.state) query.set("state", params.state);
  query.set("sort", params.sort);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/companies/*`) — never
 * the FastAPI backend directly, for the same reason `auth-service.ts`
 * doesn't: the browser never holds a bearer token to attach here
 * (ARCHITECTURE.md §1.2, §8.1). The BFF route handlers
 * (`app/api/companies/**`) attach the caller's HttpOnly access token
 * server-side and forward the request.
 */
export const companyService = {
  async listCompanies(params: CompanyListParams): Promise<CompanyListResult> {
    const { data } = await bffClient.get<ApiListEnvelope<BackendCompany>>(
      `/companies?${buildQueryString(params)}`
    );
    return { data: data.data.map(mapBackendCompany), meta: data.meta };
  },

  async getCompany(id: string): Promise<Company> {
    const { data } = await bffClient.get<BackendCompany>(`/companies/${id}`);
    return mapBackendCompany(data);
  },

  async createCompany(payload: CompanyCreateRequest): Promise<Company> {
    const { data } = await bffClient.post<BackendCompany>("/companies", payload);
    return mapBackendCompany(data);
  },

  async updateCompany(id: string, payload: CompanyUpdateRequest): Promise<Company> {
    const { data } = await bffClient.put<BackendCompany>(`/companies/${id}`, payload);
    return mapBackendCompany(data);
  },

  async deleteCompany(id: string): Promise<void> {
    await bffClient.delete(`/companies/${id}`);
  },
};
