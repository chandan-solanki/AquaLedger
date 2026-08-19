"use client";

import { useQuery } from "@tanstack/react-query";

import { userKeys } from "@/features/users/constants/query-keys";
import { userService } from "@/features/users/services/user-service";

/**
 * Options for the Audit Logs "User" filter - reuses the existing Users
 * module list endpoint (no separate actor-lookup endpoint exists, and none
 * is needed) rather than inventing a new one. Capped at the largest page
 * size the backend allows (100); a tenant with more users than that would
 * see a partial list here - acceptable for a filter dropdown on this
 * session's scope, and easy to paginate properly later if it matters.
 */
export function useActorOptions() {
  return useQuery({
    queryKey: [...userKeys.lists(), "audit-log-actor-options"] as const,
    queryFn: () =>
      userService.listUsers({ sort: "full_name", page: 1, page_size: 100 }),
    staleTime: 5 * 60 * 1000,
  });
}
