"use client";

import { useQuery } from "@tanstack/react-query";

import { fishStockKeys } from "@/features/fish-stock/constants/query-keys";
import { fishStockService } from "@/features/fish-stock/services/fish-stock-service";

/** A single fish's stock detail by id — disabled until an id is available, mirrors `useFish`. */
export function useFishStockDetail(fishId: string | undefined) {
  return useQuery({
    queryKey: fishStockKeys.detail(fishId ?? ""),
    queryFn: () => fishStockService.getFishStockDetail(fishId as string),
    enabled: Boolean(fishId),
  });
}
