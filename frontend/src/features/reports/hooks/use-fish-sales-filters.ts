"use client";

import { parseAsInteger, parseAsString, useQueryStates } from "nuqs";

import { DEFAULT_FISH_SALES_FILTERS } from "@/features/reports/schemas/fish-sales-filters";

const fishSalesFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_FISH_SALES_FILTERS.search),
  fishId: parseAsString,
  fromDate: parseAsString,
  toDate: parseAsString,
  customerId: parseAsString,
  boatId: parseAsString,
  tripId: parseAsString,
  minQuantity: parseAsString,
  minRevenue: parseAsString,
  page: parseAsInteger.withDefault(DEFAULT_FISH_SALES_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_FISH_SALES_FILTERS.pageSize),
};

/**
 * Fish Sales Analytics filter/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10), mirroring `useSalesReportFilters`.
 */
export function useFishSalesFilters() {
  return useQueryStates(fishSalesFilterParsers, { history: "push" });
}
