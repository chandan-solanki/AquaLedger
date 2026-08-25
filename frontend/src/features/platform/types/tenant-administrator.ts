import type { AccountStatus } from "@/features/auth/types/auth";

/**
 * Raw backend shape (snake_case), matching TenantAdministratorResponse
 * (app/modules/platform_admin/schemas.py) exactly - identity fields only,
 * never roles/permissions/tenant business data.
 */
export interface BackendTenantAdministrator {
  id: string;
  email: string;
  username: string;
  full_name: string;
  is_superuser: boolean;
  status: AccountStatus;
}

export interface TenantAdministrator {
  id: string;
  email: string;
  username: string;
  fullName: string;
  isSuperuser: boolean;
  status: AccountStatus;
}

export function mapBackendTenantAdministrator(
  administrator: BackendTenantAdministrator
): TenantAdministrator {
  return {
    id: administrator.id,
    email: administrator.email,
    username: administrator.username,
    fullName: administrator.full_name,
    isSuperuser: administrator.is_superuser,
    status: administrator.status,
  };
}
