"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import {
  DEFAULT_PURCHASE_BILL_FILTERS,
  PURCHASE_BILL_SORT_DIRECTIONS,
  PURCHASE_BILL_SORT_FIELDS,
} from "@/features/purchase-bills/schemas/purchase-bill-filters";
import { PURCHASE_BILL_STATUS_VALUES } from "@/features/purchase-bills/constants/purchase-bill-status";

const purchaseBillFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_PURCHASE_BILL_FILTERS.search),
  status: parseAsStringEnum([...PURCHASE_BILL_STATUS_VALUES]),
  supplier: parseAsString,
  page: parseAsInteger.withDefault(DEFAULT_PURCHASE_BILL_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_PURCHASE_BILL_FILTERS.pageSize),
  sort: parseAsStringEnum([...PURCHASE_BILL_SORT_FIELDS]).withDefault(DEFAULT_PURCHASE_BILL_FILTERS.sort),
  direction: parseAsStringEnum([...PURCHASE_BILL_SORT_DIRECTIONS]).withDefault(
    DEFAULT_PURCHASE_BILL_FILTERS.direction
  ),
};

/**
 * Purchase bill list filter/sort/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10), mirroring `useInvoiceFilters` exactly.
 */
export function usePurchaseBillFilters() {
  return useQueryStates(purchaseBillFilterParsers, { history: "push" });
}
