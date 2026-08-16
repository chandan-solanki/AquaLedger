"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import {
  DEFAULT_DELIVERY_CHALLAN_FILTERS,
  DELIVERY_CHALLAN_SORT_DIRECTIONS,
  DELIVERY_CHALLAN_SORT_FIELDS,
} from "@/features/delivery-challans/schemas/delivery-challan-filters";
import { DELIVERY_CHALLAN_STATUS_VALUES } from "@/features/delivery-challans/constants/delivery-challan-status";

const deliveryChallanFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_DELIVERY_CHALLAN_FILTERS.search),
  status: parseAsStringEnum([...DELIVERY_CHALLAN_STATUS_VALUES]),
  invoice: parseAsString,
  challanDateFrom: parseAsString,
  challanDateTo: parseAsString,
  page: parseAsInteger.withDefault(DEFAULT_DELIVERY_CHALLAN_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_DELIVERY_CHALLAN_FILTERS.pageSize),
  sort: parseAsStringEnum([...DELIVERY_CHALLAN_SORT_FIELDS]).withDefault(
    DEFAULT_DELIVERY_CHALLAN_FILTERS.sort
  ),
  direction: parseAsStringEnum([...DELIVERY_CHALLAN_SORT_DIRECTIONS]).withDefault(
    DEFAULT_DELIVERY_CHALLAN_FILTERS.direction
  ),
};

/**
 * Delivery challan list filter/sort/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10), mirroring `usePurchaseOrderFilters` exactly.
 */
export function useDeliveryChallanFilters() {
  return useQueryStates(deliveryChallanFilterParsers, { history: "push" });
}
