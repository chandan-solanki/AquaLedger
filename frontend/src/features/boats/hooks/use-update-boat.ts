"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { boatKeys } from "@/features/boats/constants/query-keys";
import { boatService } from "@/features/boats/services/boat-service";
import type { BoatUpdateRequest } from "@/features/boats/types/boat";

export interface UpdateBoatVariables {
  id: string;
  payload: BoatUpdateRequest;
}

export function useUpdateBoat() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: UpdateBoatVariables) => boatService.updateBoat(id, payload),
    onSuccess: (boat) => {
      queryClient.invalidateQueries({ queryKey: boatKeys.lists() });
      queryClient.invalidateQueries({ queryKey: boatKeys.detail(boat.id) });
    },
  });
}
