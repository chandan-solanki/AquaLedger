"use client";

import { parseAsBoolean, parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import { BOAT_STATUS_VALUES } from "@/features/boats/constants/boat-status";
import {
  BOAT_SORT_DIRECTIONS,
  BOAT_SORT_FIELDS,
  DEFAULT_BOAT_FILTERS,
} from "@/features/boats/schemas/boat-filters";

const boatFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_BOAT_FILTERS.search),
  status: parseAsStringEnum([...BOAT_STATUS_VALUES]),
  boatType: parseAsString.withDefault(DEFAULT_BOAT_FILTERS.boatType),
  insuranceExpired: parseAsBoolean,
  licenseExpired: parseAsBoolean,
  page: parseAsInteger.withDefault(DEFAULT_BOAT_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_BOAT_FILTERS.pageSize),
  sort: parseAsStringEnum([...BOAT_SORT_FIELDS]).withDefault(DEFAULT_BOAT_FILTERS.sort),
  direction: parseAsStringEnum([...BOAT_SORT_DIRECTIONS]).withDefault(DEFAULT_BOAT_FILTERS.direction),
};

/**
 * Boat list filter/sort/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10: "URL/filter state: nuqs... non-negotiable for list
 * screens users share"), mirroring `useFishFilters` exactly.
 */
export function useBoatFilters() {
  return useQueryStates(boatFilterParsers, { history: "push" });
}
