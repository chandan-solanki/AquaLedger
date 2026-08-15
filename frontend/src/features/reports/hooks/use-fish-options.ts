"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import type { ComboboxOption } from "@/components/form";
import { fishKeys, fishService } from "@/features/fish";
import type { FishListParams } from "@/features/fish";

const FISH_OPTIONS_PARAMS: FishListParams = { sort: "name", page: 1, page_size: 100 };

/**
 * Every fish for this tenant, for the Fish Sales Analytics report's Fish
 * selector - sourced from the Fish feature's own public surface
 * (`@/features/fish`), never another feature's internals (mirrors
 * `useCustomerOptions`'s own stated rule).
 */
export function useFishOptions() {
  const query = useQuery({
    queryKey: fishKeys.list(FISH_OPTIONS_PARAMS),
    queryFn: () => fishService.listFish(FISH_OPTIONS_PARAMS),
    staleTime: 5 * 60 * 1000,
  });

  const fish = query.data?.data;

  return useMemo(() => {
    const list = fish ?? [];
    return {
      options: list.map((item): ComboboxOption => ({ value: item.id, label: item.name })),
      nameById: new Map(list.map((item) => [item.id, item.name])),
      isLoading: query.isLoading,
    };
  }, [fish, query.isLoading]);
}
