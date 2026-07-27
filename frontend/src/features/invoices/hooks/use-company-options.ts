"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import type { ComboboxOption } from "@/components/form";
import { companyKeys, companyService } from "@/features/companies";
import type { CompanyListParams } from "@/features/companies";

const COMPANY_OPTIONS_PARAMS: CompanyListParams = { sort: "name", page: 1, page_size: 100 };

/**
 * All companies for this tenant, for the Invoice list's Company filter and
 * for resolving `company_id` to a display name in the Company column -
 * `InvoiceResponse` carries only `company_id` (app/modules/invoices/schemas.py),
 * never a nested company name, so the invoice list resolves it client-side
 * through the Companies feature's own public surface (`@/features/companies`)
 * rather than the backend joining it server-side (modules never reach into
 * another feature's internals directly - 07_FRONTEND_ARCHITECTURE.md §5),
 * mirroring `useBoatOptions` exactly.
 */
export function useCompanyOptions() {
  const query = useQuery({
    queryKey: companyKeys.list(COMPANY_OPTIONS_PARAMS),
    queryFn: () => companyService.listCompanies(COMPANY_OPTIONS_PARAMS),
    staleTime: 5 * 60 * 1000,
  });

  const companies = query.data?.data;

  return useMemo(() => {
    const list = companies ?? [];
    return {
      options: list.map((company): ComboboxOption => ({ value: company.id, label: company.name })),
      nameById: new Map(list.map((company) => [company.id, company.name])),
      isLoading: query.isLoading,
    };
  }, [companies, query.isLoading]);
}
