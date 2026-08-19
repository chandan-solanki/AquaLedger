"use client";

import { useQuery } from "@tanstack/react-query";

import { userKeys } from "@/features/users/constants/query-keys";
import { userService } from "@/features/users/services/user-service";

/** Roles available for assignment in the caller's tenant - excludes
 * super_admin unless the caller is themselves a superuser (backend-enforced,
 * see app/modules/users/service.py's list_role_options). Rarely changes
 * within a session, so a longer staleTime avoids refetching on every
 * Create/Edit User form mount. */
export function useRoleOptions() {
  return useQuery({
    queryKey: userKeys.roles(),
    queryFn: () => userService.listRoleOptions(),
    staleTime: 5 * 60 * 1000,
  });
}
