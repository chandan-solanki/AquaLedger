"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { fishKeys } from "@/features/fish/constants/query-keys";
import { fishService } from "@/features/fish/services/fish-service";
import type { FishUpdateRequest } from "@/features/fish/types/fish";

export interface UpdateFishVariables {
  id: string;
  payload: FishUpdateRequest;
}

export function useUpdateFish() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: UpdateFishVariables) => fishService.updateFish(id, payload),
    onSuccess: (fish) => {
      queryClient.invalidateQueries({ queryKey: fishKeys.lists() });
      queryClient.invalidateQueries({ queryKey: fishKeys.detail(fish.id) });
    },
  });
}
