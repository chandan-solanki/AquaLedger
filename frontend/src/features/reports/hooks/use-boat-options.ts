"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import type { ComboboxOption } from "@/components/form";
import { boatKeys, boatService } from "@/features/boats";
import type { BoatListParams } from "@/features/boats";

const BOAT_OPTIONS_PARAMS: BoatListParams = { sort: "name", page: 1, page_size: 100 };

/**
 * Every boat for this tenant, for the Trip/Boat Profitability reports' Boat
 * selector - sourced from the Boats feature's own public surface
 * (`@/features/boats`), never another feature's internals (mirrors
 * `useCustomerOptions`'s own stated rule, applied here so Reports doesn't
 * reach into the Trips feature's own copy of this hook).
 */
export function useBoatOptions() {
  const query = useQuery({
    queryKey: boatKeys.list(BOAT_OPTIONS_PARAMS),
    queryFn: () => boatService.listBoats(BOAT_OPTIONS_PARAMS),
    staleTime: 5 * 60 * 1000,
  });

  const boats = query.data?.data;

  return useMemo(() => {
    const list = boats ?? [];
    return {
      options: list.map((boat): ComboboxOption => ({ value: boat.id, label: boat.name })),
      nameById: new Map(list.map((boat) => [boat.id, boat.name])),
      isLoading: query.isLoading,
    };
  }, [boats, query.isLoading]);
}
