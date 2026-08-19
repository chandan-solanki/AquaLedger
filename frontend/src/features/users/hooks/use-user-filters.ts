"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import {
  DEFAULT_USER_FILTERS,
  USER_SORT_DIRECTIONS,
  USER_SORT_FIELDS,
} from "@/features/users/schemas/user-filters";
import { USER_STATUS_ACTION_VALUES } from "@/features/users/constants/user-status";

const userFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_USER_FILTERS.search),
  roleId: parseAsString,
  status: parseAsStringEnum([...USER_STATUS_ACTION_VALUES, "locked", "password_expired"]),
  page: parseAsInteger.withDefault(DEFAULT_USER_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_USER_FILTERS.pageSize),
  sort: parseAsStringEnum([...USER_SORT_FIELDS]).withDefault(DEFAULT_USER_FILTERS.sort),
  direction: parseAsStringEnum([...USER_SORT_DIRECTIONS]).withDefault(DEFAULT_USER_FILTERS.direction),
};

/**
 * Users list filter/sort/page state, synced to the URL via nuqs - mirrors
 * useCompanyFilters exactly (ARCHITECTURE.md §10).
 */
export function useUserFilters() {
  return useQueryStates(userFilterParsers, { history: "push" });
}
