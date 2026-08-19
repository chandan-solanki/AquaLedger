import { bffClient } from "@/lib/bff-client";
import type { ApiListEnvelope } from "@/types/api";
import type {
  BackendUser,
  ManagedUser,
  RoleSummary,
  UserCreateRequest,
  UserListParams,
  UserStatusAction,
  UserUpdateRequest,
} from "@/features/users/types/user";
import { mapBackendUser } from "@/features/users/types/user";

export interface UserListResult {
  data: ManagedUser[];
  meta: ApiListEnvelope<BackendUser>["meta"];
}

function buildQueryString(params: UserListParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.role_id) query.set("role_id", params.role_id);
  if (params.status) query.set("status", params.status);
  query.set("sort", params.sort);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/users/*`) - never the
 * FastAPI backend directly, same reason `company-service.ts` doesn't
 * (ARCHITECTURE.md §1.2, §8.1).
 */
export const userService = {
  async listUsers(params: UserListParams): Promise<UserListResult> {
    const { data } = await bffClient.get<ApiListEnvelope<BackendUser>>(`/users?${buildQueryString(params)}`);
    return { data: data.data.map(mapBackendUser), meta: data.meta };
  },

  async getUser(id: string): Promise<ManagedUser> {
    const { data } = await bffClient.get<BackendUser>(`/users/${id}`);
    return mapBackendUser(data);
  },

  async createUser(payload: UserCreateRequest): Promise<ManagedUser> {
    const { data } = await bffClient.post<BackendUser>("/users", payload);
    return mapBackendUser(data);
  },

  async updateUser(id: string, payload: UserUpdateRequest): Promise<ManagedUser> {
    const { data } = await bffClient.put<BackendUser>(`/users/${id}`, payload);
    return mapBackendUser(data);
  },

  async updateUserStatus(id: string, status: UserStatusAction): Promise<ManagedUser> {
    const { data } = await bffClient.patch<BackendUser>(`/users/${id}/status`, { status });
    return mapBackendUser(data);
  },

  async listRoleOptions(): Promise<RoleSummary[]> {
    const { data } = await bffClient.get<RoleSummary[]>("/users/roles");
    return data;
  },
};
