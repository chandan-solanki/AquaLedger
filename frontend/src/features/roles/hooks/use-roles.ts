"use client";

import { useQuery } from "@tanstack/react-query";

import { roleKeys } from "@/features/roles/constants/query-keys";
import { roleService } from "@/features/roles/services/role-service";

/** Every role for the caller's tenant - unpaginated (the backend never
 * paginates this list; a tenant's role count is small by design, matching
 * the fixed system-role set today). Client-side search/sort happens in the
 * owning page, not here. */
export function useRoles() {
  return useQuery({
    queryKey: roleKeys.lists(),
    queryFn: () => roleService.listRoles(),
  });
}
