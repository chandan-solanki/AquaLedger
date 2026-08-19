"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { companyProfileKeys } from "@/features/company-profile/constants/query-keys";
import { companyProfileService } from "@/features/company-profile/services/company-profile-service";

export function useDeleteCompanyLogo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => companyProfileService.deleteCompanyLogo(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: companyProfileKeys.detail() });
    },
  });
}
