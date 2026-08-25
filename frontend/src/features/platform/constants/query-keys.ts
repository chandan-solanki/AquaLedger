import type { TenantListParams } from "@/features/platform/types/tenant";

export const platformTenantKeys = {
  all: () => ["platform", "tenants"] as const,
  lists: () => [...platformTenantKeys.all(), "list"] as const,
  list: (params: TenantListParams) => [...platformTenantKeys.lists(), params] as const,
  details: () => [...platformTenantKeys.all(), "detail"] as const,
  detail: (id: string) => [...platformTenantKeys.details(), id] as const,
};

/** No params - GET /platform/dashboard takes none, mirrors dashboardKeys' own fixed-key shape. */
export const platformDashboardKeys = {
  all: () => ["platform", "dashboard"] as const,
  summary: () => [...platformDashboardKeys.all(), "summary"] as const,
};

export const platformTenantAdministratorKeys = {
  all: (tenantId: string) => [...platformTenantKeys.detail(tenantId), "administrators"] as const,
  list: (tenantId: string) => [...platformTenantAdministratorKeys.all(tenantId), "list"] as const,
};
