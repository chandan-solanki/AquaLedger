import { bffClient } from "@/lib/bff-client";
import type {
  BackendTenantAdministrator,
  TenantAdministrator,
} from "@/features/platform/types/tenant-administrator";
import { mapBackendTenantAdministrator } from "@/features/platform/types/tenant-administrator";

/**
 * Talks only to the Next.js BFF's own routes
 * (`/api/platform/tenants/*\/administrators*`) — never the FastAPI backend
 * directly, same rationale as `tenant-service.ts`.
 */
export const platformTenantAdministratorService = {
  async listAdministrators(tenantId: string): Promise<TenantAdministrator[]> {
    const { data } = await bffClient.get<BackendTenantAdministrator[]>(
      `/platform/tenants/${tenantId}/administrators`
    );
    return data.map(mapBackendTenantAdministrator);
  },

  async resetPassword(
    tenantId: string,
    userId: string,
    newPassword: string
  ): Promise<TenantAdministrator> {
    const { data } = await bffClient.patch<BackendTenantAdministrator>(
      `/platform/tenants/${tenantId}/administrators/${userId}/password`,
      { new_password: newPassword }
    );
    return mapBackendTenantAdministrator(data);
  },
};
