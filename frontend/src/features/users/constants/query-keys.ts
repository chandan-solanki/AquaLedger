import type { UserListParams } from "@/features/users/types/user";

export const userKeys = {
  all: () => ["users"] as const,
  lists: () => [...userKeys.all(), "list"] as const,
  list: (params: UserListParams) => [...userKeys.lists(), params] as const,
  details: () => [...userKeys.all(), "detail"] as const,
  detail: (id: string) => [...userKeys.details(), id] as const,
  roles: () => [...userKeys.all(), "roles"] as const,
};
