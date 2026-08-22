"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { userKeys } from "@/features/users/constants/query-keys";
import { userService } from "@/features/users/services/user-service";

export interface ResetUserPasswordVariables {
  id: string;
  newPassword: string;
}

/**
 * No onError toast here, unlike useUpdateUserStatus - a weak-password 422
 * needs to land on the dialog's own New Password field, and the special
 * "cannot reset your own password"/"requires a superuser" cases read
 * better as an inline dialog message than a toast, so ResetPasswordDialog
 * owns its own try/catch (same division as useUpdateUser/ProfileForm).
 */
export function useResetUserPassword() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, newPassword }: ResetUserPasswordVariables) =>
      userService.resetUserPassword(id, newPassword),
    onSuccess: (user) => {
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });
      queryClient.invalidateQueries({ queryKey: userKeys.detail(user.id) });
    },
  });
}
