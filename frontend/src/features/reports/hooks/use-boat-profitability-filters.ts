"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import {
  BOAT_PROFITABILITY_PROFITABILITY_VALUES,
  DEFAULT_BOAT_PROFITABILITY_FILTERS,
} from "@/features/reports/schemas/boat-profitability-filters";

const boatProfitabilityFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_BOAT_PROFITABILITY_FILTERS.search),
  boatId: parseAsString,
  fromDate: parseAsString,
  toDate: parseAsString,
  minTrips: parseAsInteger,
  profitability: parseAsStringEnum([...BOAT_PROFITABILITY_PROFITABILITY_VALUES]),
  page: parseAsInteger.withDefault(DEFAULT_BOAT_PROFITABILITY_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_BOAT_PROFITABILITY_FILTERS.pageSize),
};

/**
 * Boat Profitability filter/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10), mirroring `useTripProfitabilityFilters`.
 */
export function useBoatProfitabilityFilters() {
  return useQueryStates(boatProfitabilityFilterParsers, { history: "push" });
}
