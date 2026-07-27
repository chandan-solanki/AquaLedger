"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import type { ComboboxOption } from "@/components/form";
import { boatKeys, boatService } from "@/features/boats";
import type { BoatListParams } from "@/features/boats";

const BOAT_OPTIONS_PARAMS: BoatListParams = { sort: "name", page: 1, page_size: 100 };

/**
 * All boats for this tenant, for the Trip list's Boat filter and for
 * resolving `boat_id` to a display name in the Boat column - `TripResponse`
 * carries only `boat_id` (app/modules/trips/schemas.py), never a nested
 * boat name, so the trip list resolves it client-side through the Boats
 * feature's own public surface (`@/features/boats`) rather than the backend
 * joining it server-side (modules never reach into another feature's
 * internals directly - 07_FRONTEND_ARCHITECTURE.md §5).
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
