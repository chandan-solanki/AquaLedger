"use client";

import { useQuery } from "@tanstack/react-query";

import { roleKeys } from "@/features/roles/constants/query-keys";
import { roleService } from "@/features/roles/services/role-service";

/**
 * The full, global permission catalog - named "Catalog" (not `usePermissions`,
 * which already exists at `@/features/auth/hooks/use-permissions` for the
 * *current user's own* permission checks) to avoid confusion between "every
 * permission that exists" and "what the logged-in caller holds". Rarely
 * changes within a session, so a longer staleTime avoids refetching on
 * every Role Detail page visit.
 */
export function usePermissionsCatalog() {
  return useQuery({
    queryKey: roleKeys.permissions(),
    queryFn: () => roleService.listPermissions(),
    staleTime: 5 * 60 * 1000,
  });
}
