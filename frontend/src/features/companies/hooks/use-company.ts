"use client";

import { useQuery } from "@tanstack/react-query";

import { companyKeys } from "@/features/companies/constants/query-keys";
import { companyService } from "@/features/companies/services/company-service";

/** A single company by id — disabled until an id is available. */
export function useCompany(id: string | undefined) {
  return useQuery({
    queryKey: companyKeys.detail(id ?? ""),
    queryFn: () => companyService.getCompany(id as string),
    enabled: Boolean(id),
  });
}
