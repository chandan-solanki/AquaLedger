"use client";

import { useQuery } from "@tanstack/react-query";

import { fishKeys } from "@/features/fish/constants/query-keys";
import { fishService } from "@/features/fish/services/fish-service";

/** A single fish record by id — disabled until an id is available. */
export function useFish(id: string | undefined) {
  return useQuery({
    queryKey: fishKeys.detail(id ?? ""),
    queryFn: () => fishService.getFish(id as string),
    enabled: Boolean(id),
  });
}
