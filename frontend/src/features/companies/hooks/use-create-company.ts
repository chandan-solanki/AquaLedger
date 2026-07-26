"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { companyKeys } from "@/features/companies/constants/query-keys";
import { companyService } from "@/features/companies/services/company-service";
import type { CompanyCreateRequest } from "@/features/companies/types/company";

export function useCreateCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CompanyCreateRequest) => companyService.createCompany(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: companyKeys.lists() });
    },
  });
}
