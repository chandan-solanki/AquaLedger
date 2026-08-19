"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { companyProfileKeys } from "@/features/company-profile/constants/query-keys";
import { companyProfileService } from "@/features/company-profile/services/company-profile-service";

export function useUploadCompanyLogo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => companyProfileService.uploadCompanyLogo(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: companyProfileKeys.detail() });
    },
  });
}
