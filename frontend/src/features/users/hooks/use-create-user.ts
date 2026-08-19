"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { userKeys } from "@/features/users/constants/query-keys";
import { userService } from "@/features/users/services/user-service";
import type { UserCreateRequest } from "@/features/users/types/user";

export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: UserCreateRequest) => userService.createUser(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });
    },
  });
}
