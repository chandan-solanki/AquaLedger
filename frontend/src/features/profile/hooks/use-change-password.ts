"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { authKeys } from "@/features/auth/constants/query-keys";
import { profileService } from "@/features/profile/services/profile-service";

/**
 * Invalidates the auth session query on success, same as every other
 * profile mutation - a password change can flip status from
 * password_expired to active, which the session query's `/auth/me` fetch
 * should pick up (see profile-page.tsx's status badge).
 */
export function useChangePassword() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: profileService.changePassword,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: authKeys.session() });
    },
  });
}
