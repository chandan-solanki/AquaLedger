"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import { FISH_STOCK_STATUS_VALUES } from "@/features/fish-stock/constants/fish-stock-status";
import { DEFAULT_FISH_STOCK_FILTERS } from "@/features/fish-stock/schemas/fish-stock-filters";

const fishStockFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_FISH_STOCK_FILTERS.search),
  status: parseAsStringEnum([...FISH_STOCK_STATUS_VALUES]),
  page: parseAsInteger.withDefault(DEFAULT_FISH_STOCK_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_FISH_STOCK_FILTERS.pageSize),
};

/**
 * Fish Stock list filter/sort/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10), mirroring `useFishFilters` exactly.
 */
export function useFishStockFilters() {
  return useQueryStates(fishStockFilterParsers, { history: "push" });
}
