"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { userKeys } from "@/features/users/constants/query-keys";
import { userService } from "@/features/users/services/user-service";
import type { UserStatusAction } from "@/features/users/types/user";
import { toastError, toastSuccess } from "@/lib/toast";
import { normalizeApiError } from "@/utils/api-error";

export interface UpdateUserStatusVariables {
  id: string;
  status: UserStatusAction;
}

/**
 * Owns the full activate/deactivate outcome (cache invalidation + toast) so
 * both the List page's row action and the Detail page's action button get
 * identical behavior - mirrors useDeleteCompany's centralization rationale.
 * No navigation on success (unlike delete): the record still exists, just
 * with a new status, so both call sites stay put and let the invalidated
 * query re-render in place.
 */
export function useUpdateUserStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, status }: UpdateUserStatusVariables) => userService.updateUserStatus(id, status),
    onSuccess: (user) => {
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });
      queryClient.invalidateQueries({ queryKey: userKeys.detail(user.id) });
      toastSuccess(user.status === "inactive" ? `${user.fullName} was deactivated.` : `${user.fullName} was activated.`);
    },
    onError: (error) => {
      toastError(normalizeApiError(error).message);
    },
  });
}
