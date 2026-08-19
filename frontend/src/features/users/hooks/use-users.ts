"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { userKeys } from "@/features/users/constants/query-keys";
import type { UserFilters } from "@/features/users/schemas/user-filters";
import { toUserListParams } from "@/features/users/schemas/user-filters";
import { userService } from "@/features/users/services/user-service";

/** Server-side, paginated users list - mirrors useCompanies exactly. */
export function useUsers(filters: UserFilters) {
  const params = toUserListParams(filters);

  return useQuery({
    queryKey: userKeys.list(params),
    queryFn: () => userService.listUsers(params),
    placeholderData: keepPreviousData,
  });
}
