import { bffClient } from "@/lib/bff-client";
import type {
  BackendRoleDetail,
  BackendRoleListItem,
  PermissionSummary,
  RoleDetail,
  RoleListItem,
} from "@/features/roles/types/role";
import { mapBackendRoleDetail, mapBackendRoleListItem } from "@/features/roles/types/role";

/**
 * Talks only to the Next.js BFF's own routes (`/api/roles/*`) - same
 * reason `user-service.ts` doesn't call the FastAPI backend directly
 * (ARCHITECTURE.md Sec 1.2, Sec 8.1). Read-only: there is no
 * create/update/delete method here - see the backend router's module
 * docstring (app/modules/roles/router.py) for why.
 */
export const roleService = {
  async listRoles(): Promise<RoleListItem[]> {
    const { data } = await bffClient.get<BackendRoleListItem[]>("/roles");
    return data.map(mapBackendRoleListItem);
  },

  async getRole(id: string): Promise<RoleDetail> {
    const { data } = await bffClient.get<BackendRoleDetail>(`/roles/${id}`);
    return mapBackendRoleDetail(data);
  },

  async listPermissions(): Promise<PermissionSummary[]> {
    const { data } = await bffClient.get<PermissionSummary[]>("/roles/permissions");
    return data;
  },
};
