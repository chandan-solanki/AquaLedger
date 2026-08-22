"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { authKeys } from "@/features/auth/constants/query-keys";
import { profileService } from "@/features/profile/services/profile-service";

export function useUploadAvatar() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => profileService.uploadAvatar(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: authKeys.session() });
    },
  });
}
