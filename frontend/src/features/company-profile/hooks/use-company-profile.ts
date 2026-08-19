"use client";

import { useQuery } from "@tanstack/react-query";

import { companyProfileKeys } from "@/features/company-profile/constants/query-keys";
import { companyProfileService } from "@/features/company-profile/services/company-profile-service";

/** The caller's own tenant profile - always exactly one row (backend auto-vivifies on first GET), no id param needed. */
export function useCompanyProfile() {
  return useQuery({
    queryKey: companyProfileKeys.detail(),
    queryFn: () => companyProfileService.getCompanyProfile(),
  });
}
