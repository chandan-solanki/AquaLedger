"use client";

import { useQuery } from "@tanstack/react-query";

import { platformTenantAdministratorKeys } from "@/features/platform/constants/query-keys";
import { platformTenantAdministratorService } from "@/features/platform/services/tenant-administrator-service";

/**
 * The tenant detail page's "Administrators" section — lets a platform admin
 * see who they'd be targeting before offering a password reset. Identity
 * fields only; never fetched as part of any business-data view.
 */
export function useTenantAdministrators(tenantId: string) {
  return useQuery({
    queryKey: platformTenantAdministratorKeys.list(tenantId),
    queryFn: () => platformTenantAdministratorService.listAdministrators(tenantId),
  });
}
