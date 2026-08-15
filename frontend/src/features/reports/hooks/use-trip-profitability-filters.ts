"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import {
  DEFAULT_TRIP_PROFITABILITY_FILTERS,
  TRIP_PROFITABILITY_PROFITABILITY_VALUES,
} from "@/features/reports/schemas/trip-profitability-filters";

const tripProfitabilityFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_TRIP_PROFITABILITY_FILTERS.search),
  boatId: parseAsString,
  fromDate: parseAsString,
  toDate: parseAsString,
  profitability: parseAsStringEnum([...TRIP_PROFITABILITY_PROFITABILITY_VALUES]),
  page: parseAsInteger.withDefault(DEFAULT_TRIP_PROFITABILITY_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_TRIP_PROFITABILITY_FILTERS.pageSize),
};

/**
 * Trip Profitability filter/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10), mirroring `useSalesReportFilters`.
 */
export function useTripProfitabilityFilters() {
  return useQueryStates(tripProfitabilityFilterParsers, { history: "push" });
}
