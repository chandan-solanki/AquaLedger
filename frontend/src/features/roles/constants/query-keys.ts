export const roleKeys = {
  all: () => ["roles"] as const,
  lists: () => [...roleKeys.all(), "list"] as const,
  details: () => [...roleKeys.all(), "detail"] as const,
  detail: (id: string) => [...roleKeys.details(), id] as const,
  permissions: () => [...roleKeys.all(), "permissions"] as const,
};
