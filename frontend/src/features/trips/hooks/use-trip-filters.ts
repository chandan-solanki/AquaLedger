"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import { TRIP_STATUS_VALUES } from "@/features/trips/constants/trip-status";
import {
  DEFAULT_TRIP_FILTERS,
  TRIP_SORT_DIRECTIONS,
  TRIP_SORT_FIELDS,
} from "@/features/trips/schemas/trip-filters";

const tripFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_TRIP_FILTERS.search),
  status: parseAsStringEnum([...TRIP_STATUS_VALUES]),
  boat: parseAsString,
  page: parseAsInteger.withDefault(DEFAULT_TRIP_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_TRIP_FILTERS.pageSize),
  sort: parseAsStringEnum([...TRIP_SORT_FIELDS]).withDefault(DEFAULT_TRIP_FILTERS.sort),
  direction: parseAsStringEnum([...TRIP_SORT_DIRECTIONS]).withDefault(DEFAULT_TRIP_FILTERS.direction),
};

/**
 * Trip list filter/sort/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10: "URL/filter state: nuqs... non-negotiable for list
 * screens users share"), mirroring `useBoatFilters` exactly.
 */
export function useTripFilters() {
  return useQueryStates(tripFilterParsers, { history: "push" });
}
