"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import { FISH_STATUS_VALUES } from "@/features/fish/constants/fish-status";
import {
  DEFAULT_FISH_FILTERS,
  FISH_SORT_DIRECTIONS,
  FISH_SORT_FIELDS,
} from "@/features/fish/schemas/fish-filters";
import { FISH_UNIT_VALUES } from "@/features/fish/types/fish";

const fishFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_FISH_FILTERS.search),
  status: parseAsStringEnum([...FISH_STATUS_VALUES]),
  category: parseAsString.withDefault(DEFAULT_FISH_FILTERS.category),
  unit: parseAsStringEnum([...FISH_UNIT_VALUES]),
  page: parseAsInteger.withDefault(DEFAULT_FISH_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_FISH_FILTERS.pageSize),
  sort: parseAsStringEnum([...FISH_SORT_FIELDS]).withDefault(DEFAULT_FISH_FILTERS.sort),
  direction: parseAsStringEnum([...FISH_SORT_DIRECTIONS]).withDefault(DEFAULT_FISH_FILTERS.direction),
};

/**
 * Fish list filter/sort/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10: "URL/filter state: nuqs... non-negotiable for list
 * screens users share"), mirroring `useCompanyFilters` exactly.
 */
export function useFishFilters() {
  return useQueryStates(fishFilterParsers, { history: "push" });
}
