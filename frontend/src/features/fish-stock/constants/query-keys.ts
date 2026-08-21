import type { FishStockListParams } from "@/features/fish-stock/types/fish-stock";

export const fishStockKeys = {
  all: () => ["fish-stock"] as const,
  lists: () => [...fishStockKeys.all(), "list"] as const,
  list: (params: FishStockListParams) => [...fishStockKeys.lists(), params] as const,
  details: () => [...fishStockKeys.all(), "detail"] as const,
  detail: (fishId: string) => [...fishStockKeys.details(), fishId] as const,
};
