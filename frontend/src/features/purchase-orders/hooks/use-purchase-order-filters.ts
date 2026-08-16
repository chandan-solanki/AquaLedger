"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import {
  DEFAULT_PURCHASE_ORDER_FILTERS,
  PURCHASE_ORDER_SORT_DIRECTIONS,
  PURCHASE_ORDER_SORT_FIELDS,
} from "@/features/purchase-orders/schemas/purchase-order-filters";
import { PURCHASE_ORDER_STATUS_VALUES } from "@/features/purchase-orders/constants/purchase-order-status";

const purchaseOrderFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_PURCHASE_ORDER_FILTERS.search),
  status: parseAsStringEnum([...PURCHASE_ORDER_STATUS_VALUES]),
  supplier: parseAsString,
  orderDateFrom: parseAsString,
  orderDateTo: parseAsString,
  page: parseAsInteger.withDefault(DEFAULT_PURCHASE_ORDER_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_PURCHASE_ORDER_FILTERS.pageSize),
  sort: parseAsStringEnum([...PURCHASE_ORDER_SORT_FIELDS]).withDefault(DEFAULT_PURCHASE_ORDER_FILTERS.sort),
  direction: parseAsStringEnum([...PURCHASE_ORDER_SORT_DIRECTIONS]).withDefault(
    DEFAULT_PURCHASE_ORDER_FILTERS.direction
  ),
};

/**
 * Purchase order list filter/sort/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10), mirroring `usePurchaseBillFilters` exactly.
 */
export function usePurchaseOrderFilters() {
  return useQueryStates(purchaseOrderFilterParsers, { history: "push" });
}
