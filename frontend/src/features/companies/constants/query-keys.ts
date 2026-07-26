import type { CompanyListParams } from "@/features/companies/types/company";

export const companyKeys = {
  all: () => ["companies"] as const,
  lists: () => [...companyKeys.all(), "list"] as const,
  list: (params: CompanyListParams) => [...companyKeys.lists(), params] as const,
  details: () => [...companyKeys.all(), "detail"] as const,
  detail: (id: string) => [...companyKeys.details(), id] as const,
};
