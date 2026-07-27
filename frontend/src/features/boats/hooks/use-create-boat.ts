"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { boatKeys } from "@/features/boats/constants/query-keys";
import { boatService } from "@/features/boats/services/boat-service";
import type { BoatCreateRequest } from "@/features/boats/types/boat";

export function useCreateBoat() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: BoatCreateRequest) => boatService.createBoat(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: boatKeys.lists() });
    },
  });
}
