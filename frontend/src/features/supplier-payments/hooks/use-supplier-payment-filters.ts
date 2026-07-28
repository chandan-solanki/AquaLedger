"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import { SUPPLIER_PAYMENT_METHOD_VALUES } from "@/features/supplier-payments/constants/supplier-payment-method";
import { SUPPLIER_PAYMENT_STATUS_VALUES } from "@/features/supplier-payments/constants/supplier-payment-status";
import {
  DEFAULT_SUPPLIER_PAYMENT_FILTERS,
  SUPPLIER_PAYMENT_SORT_DIRECTIONS,
  SUPPLIER_PAYMENT_SORT_FIELDS,
} from "@/features/supplier-payments/schemas/supplier-payment-filters";

const supplierPaymentFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_SUPPLIER_PAYMENT_FILTERS.search),
  status: parseAsStringEnum([...SUPPLIER_PAYMENT_STATUS_VALUES]),
  supplier: parseAsString,
  method: parseAsStringEnum([...SUPPLIER_PAYMENT_METHOD_VALUES]),
  page: parseAsInteger.withDefault(DEFAULT_SUPPLIER_PAYMENT_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_SUPPLIER_PAYMENT_FILTERS.pageSize),
  sort: parseAsStringEnum([...SUPPLIER_PAYMENT_SORT_FIELDS]).withDefault(
    DEFAULT_SUPPLIER_PAYMENT_FILTERS.sort
  ),
  direction: parseAsStringEnum([...SUPPLIER_PAYMENT_SORT_DIRECTIONS]).withDefault(
    DEFAULT_SUPPLIER_PAYMENT_FILTERS.direction
  ),
};

/**
 * Supplier payment list filter/sort/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10: "URL/filter state: nuqs... non-negotiable for list
 * screens users share"), mirroring `usePaymentFilters` exactly.
 */
export function useSupplierPaymentFilters() {
  return useQueryStates(supplierPaymentFilterParsers, { history: "push" });
}
