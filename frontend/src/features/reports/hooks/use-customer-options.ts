"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import type { ComboboxOption } from "@/components/form";
import { companyKeys, companyService } from "@/features/companies";
import type { CompanyListParams } from "@/features/companies";

const CUSTOMER_OPTIONS_PARAMS: CompanyListParams = { sort: "name", page: 1, page_size: 100 };

/**
 * Every company for this tenant, for the Customer Ledger's Customer
 * selector - sourced from the Companies feature's own public surface
 * (`@/features/companies`), never another feature's internals (mirrors
 * `useCompanyOptions` in the Invoices feature exactly, applied here so
 * Reports doesn't reach into Invoices for it).
 */
export function useCustomerOptions() {
  const query = useQuery({
    queryKey: companyKeys.list(CUSTOMER_OPTIONS_PARAMS),
    queryFn: () => companyService.listCompanies(CUSTOMER_OPTIONS_PARAMS),
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
