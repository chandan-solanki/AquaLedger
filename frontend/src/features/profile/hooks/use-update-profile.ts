"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { authKeys } from "@/features/auth/constants/query-keys";
import { profileService } from "@/features/profile/services/profile-service";

/**
 * Invalidates the auth session query on success (not a separate "profile"
 * cache key - there isn't one) so `useCurrentUser()`/`UserMenu`/the header
 * pick up the new full_name/username/phone through the one existing
 * session source of truth, the same way `useAuth().refreshUser()` already
 * does after other auth-affecting actions.
 */
export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: profileService.updateProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: authKeys.session() });
    },
  });
}
