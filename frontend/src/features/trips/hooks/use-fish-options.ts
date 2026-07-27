"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import type { ComboboxOption } from "@/components/form";
import { fishKeys, fishService } from "@/features/fish";
import type { Fish, FishListParams } from "@/features/fish";

const FISH_OPTIONS_PARAMS: FishListParams = { sort: "name", page: 1, page_size: 100 };

/**
 * All fish for this tenant - `options` for the Trip Catch form's Fish
 * `SearchableSelect` (Session 6), `fishById` for resolving `fish_id` to a
 * display name/unit in the Trip Catch table (Session 4). `TripCatchResponse`
 * carries only `fish_id` (app/modules/trip_catches/schemas.py), never a
 * nested fish object, so the Fish record is resolved client-side through the
 * Fish feature's own public surface (`@/features/fish`), mirroring
 * `use-boat-options.ts` exactly.
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
      options: list.map((f): ComboboxOption => ({ value: f.id, label: f.name })),
      fishById: new Map<string, Fish>(list.map((f) => [f.id, f])),
      isLoading: query.isLoading,
    };
  }, [fish, query.isLoading]);
}
