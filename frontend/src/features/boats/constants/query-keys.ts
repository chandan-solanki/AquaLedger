import type { BoatListParams } from "@/features/boats/types/boat";

export const boatKeys = {
  all: () => ["boats"] as const,
  lists: () => [...boatKeys.all(), "list"] as const,
  list: (params: BoatListParams) => [...boatKeys.lists(), params] as const,
  details: () => [...boatKeys.all(), "detail"] as const,
  detail: (id: string) => [...boatKeys.details(), id] as const,
};
