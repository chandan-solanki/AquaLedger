"use client";

import { useQuery } from "@tanstack/react-query";

import { platformTenantKeys } from "@/features/platform/constants/query-keys";
import { platformTenantService } from "@/features/platform/services/tenant-service";

/** A single tenant by id — disabled until an id is available. */
export function useTenant(id: string | undefined) {
  return useQuery({
    queryKey: platformTenantKeys.detail(id ?? ""),
    queryFn: () => platformTenantService.getTenant(id as string),
    enabled: Boolean(id),
  });
}
