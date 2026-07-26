import type { FishListParams } from "@/features/fish/types/fish";

export const fishKeys = {
  all: () => ["fish"] as const,
  lists: () => [...fishKeys.all(), "list"] as const,
  list: (params: FishListParams) => [...fishKeys.lists(), params] as const,
  details: () => [...fishKeys.all(), "detail"] as const,
  detail: (id: string) => [...fishKeys.details(), id] as const,
};
