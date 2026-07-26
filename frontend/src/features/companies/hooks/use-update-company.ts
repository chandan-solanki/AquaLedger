"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { companyKeys } from "@/features/companies/constants/query-keys";
import { companyService } from "@/features/companies/services/company-service";
import type { CompanyUpdateRequest } from "@/features/companies/types/company";

export interface UpdateCompanyVariables {
  id: string;
  payload: CompanyUpdateRequest;
}

export function useUpdateCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: UpdateCompanyVariables) => companyService.updateCompany(id, payload),
    onSuccess: (company) => {
      queryClient.invalidateQueries({ queryKey: companyKeys.lists() });
      queryClient.invalidateQueries({ queryKey: companyKeys.detail(company.id) });
    },
  });
}
