"use client";

import { useQuery } from "@tanstack/react-query";

import { roleKeys } from "@/features/roles/constants/query-keys";
import { roleService } from "@/features/roles/services/role-service";

/** A single role's full permission set and current members - disabled until an id is available. */
export function useRole(id: string | undefined) {
  return useQuery({
    queryKey: roleKeys.detail(id ?? ""),
    queryFn: () => roleService.getRole(id as string),
    enabled: Boolean(id),
  });
}
