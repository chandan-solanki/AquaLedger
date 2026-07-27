"use client";

import { useQuery } from "@tanstack/react-query";

import { boatKeys } from "@/features/boats/constants/query-keys";
import { boatService } from "@/features/boats/services/boat-service";

/** A single boat record by id — disabled until an id is available. */
export function useBoat(id: string | undefined) {
  return useQuery({
    queryKey: boatKeys.detail(id ?? ""),
    queryFn: () => boatService.getBoat(id as string),
    enabled: Boolean(id),
  });
}
