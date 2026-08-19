"use client";

import { useQuery } from "@tanstack/react-query";

import { userKeys } from "@/features/users/constants/query-keys";
import { userService } from "@/features/users/services/user-service";

/** A single user by id - disabled until an id is available. */
export function useUser(id: string | undefined) {
  return useQuery({
    queryKey: userKeys.detail(id ?? ""),
    queryFn: () => userService.getUser(id as string),
    enabled: Boolean(id),
  });
}
