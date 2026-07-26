"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import { COMPANY_STATUS_VALUES } from "@/features/companies/constants/company-status";
import {
  COMPANY_SORT_DIRECTIONS,
  COMPANY_SORT_FIELDS,
  DEFAULT_COMPANY_FILTERS,
} from "@/features/companies/schemas/company-filters";

const companyFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_COMPANY_FILTERS.search),
  status: parseAsStringEnum([...COMPANY_STATUS_VALUES]),
  city: parseAsString.withDefault(DEFAULT_COMPANY_FILTERS.city),
  page: parseAsInteger.withDefault(DEFAULT_COMPANY_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_COMPANY_FILTERS.pageSize),
  sort: parseAsStringEnum([...COMPANY_SORT_FIELDS]).withDefault(DEFAULT_COMPANY_FILTERS.sort),
  direction: parseAsStringEnum([...COMPANY_SORT_DIRECTIONS]).withDefault(DEFAULT_COMPANY_FILTERS.direction),
};

/**
 * Companies list filter/sort/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10: "URL/filter state: nuqs... non-negotiable for list
 * screens users share"). `history: "push"` gives every filter/page/sort
 * change its own browser history entry, so Back/Forward step through the
 * list's previous states instead of just leaving the page; `shallow: true`
 * (nuqs's default) keeps that client-side — no Next.js server round trip,
 * TanStack Query's `useCompanies` is what actually reacts and refetches.
 * A refresh or a pasted/shared URL restores the exact same state, since it
 * lives in the URL rather than component state.
 */
export function useCompanyFilters() {
  return useQueryStates(companyFilterParsers, { history: "push" });
}
