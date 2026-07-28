"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import { SUPPLIER_STATUS_VALUES } from "@/features/suppliers/constants/supplier-status";
import {
  DEFAULT_SUPPLIER_FILTERS,
  SUPPLIER_SORT_DIRECTIONS,
  SUPPLIER_SORT_FIELDS,
} from "@/features/suppliers/schemas/supplier-filters";

const supplierFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_SUPPLIER_FILTERS.search),
  status: parseAsStringEnum([...SUPPLIER_STATUS_VALUES]),
  city: parseAsString.withDefault(DEFAULT_SUPPLIER_FILTERS.city),
  page: parseAsInteger.withDefault(DEFAULT_SUPPLIER_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_SUPPLIER_FILTERS.pageSize),
  sort: parseAsStringEnum([...SUPPLIER_SORT_FIELDS]).withDefault(DEFAULT_SUPPLIER_FILTERS.sort),
  direction: parseAsStringEnum([...SUPPLIER_SORT_DIRECTIONS]).withDefault(DEFAULT_SUPPLIER_FILTERS.direction),
};

/**
 * Suppliers list filter/sort/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10), mirroring `useCompanyFilters` exactly.
 */
export function useSupplierFilters() {
  return useQueryStates(supplierFilterParsers, { history: "push" });
}
