"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { fishKeys } from "@/features/fish/constants/query-keys";
import { fishService } from "@/features/fish/services/fish-service";
import type { FishCreateRequest } from "@/features/fish/types/fish";

export function useCreateFish() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: FishCreateRequest) => fishService.createFish(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fishKeys.lists() });
    },
  });
}
