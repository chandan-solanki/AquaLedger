"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { userKeys } from "@/features/users/constants/query-keys";
import { userService } from "@/features/users/services/user-service";
import type { UserUpdateRequest } from "@/features/users/types/user";

export interface UpdateUserVariables {
  id: string;
  payload: UserUpdateRequest;
}

export function useUpdateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: UpdateUserVariables) => userService.updateUser(id, payload),
    onSuccess: (user) => {
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });
      queryClient.invalidateQueries({ queryKey: userKeys.detail(user.id) });
    },
  });
}
