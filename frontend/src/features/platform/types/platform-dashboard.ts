import type { BackendTenant, Tenant } from "@/features/platform/types/tenant";
import { mapBackendTenant } from "@/features/platform/types/tenant";

/**
 * Raw backend shape (snake_case), matching PlatformDashboardResponse
 * (app/modules/platform_admin/schemas.py) exactly - tenant lifecycle counts
 * plus the most recently provisioned tenants, never any tenant's business
 * data.
 */
export interface BackendPlatformDashboard {
  total_tenants: number;
  active_tenants: number;
  suspended_tenants: number;
  inactive_tenants: number;
  recent_tenants: BackendTenant[];
}

export interface PlatformDashboardData {
  totalTenants: number;
  activeTenants: number;
  suspendedTenants: number;
  inactiveTenants: number;
  recentTenants: Tenant[];
}

export function mapBackendPlatformDashboard(data: BackendPlatformDashboard): PlatformDashboardData {
  return {
    totalTenants: data.total_tenants,
    activeTenants: data.active_tenants,
    suspendedTenants: data.suspended_tenants,
    inactiveTenants: data.inactive_tenants,
    recentTenants: data.recent_tenants.map(mapBackendTenant),
  };
}
