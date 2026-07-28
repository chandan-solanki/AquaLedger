"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import { PAYMENT_METHOD_VALUES } from "@/features/payments/constants/payment-method";
import { PAYMENT_STATUS_VALUES } from "@/features/payments/constants/payment-status";
import {
  DEFAULT_PAYMENT_FILTERS,
  PAYMENT_SORT_DIRECTIONS,
  PAYMENT_SORT_FIELDS,
} from "@/features/payments/schemas/payment-filters";

const paymentFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_PAYMENT_FILTERS.search),
  status: parseAsStringEnum([...PAYMENT_STATUS_VALUES]),
  company: parseAsString,
  method: parseAsStringEnum([...PAYMENT_METHOD_VALUES]),
  page: parseAsInteger.withDefault(DEFAULT_PAYMENT_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_PAYMENT_FILTERS.pageSize),
  sort: parseAsStringEnum([...PAYMENT_SORT_FIELDS]).withDefault(DEFAULT_PAYMENT_FILTERS.sort),
  direction: parseAsStringEnum([...PAYMENT_SORT_DIRECTIONS]).withDefault(DEFAULT_PAYMENT_FILTERS.direction),
};

/**
 * Payment list filter/sort/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10: "URL/filter state: nuqs... non-negotiable for list
 * screens users share"), mirroring `useInvoiceFilters` exactly.
 */
export function usePaymentFilters() {
  return useQueryStates(paymentFilterParsers, { history: "push" });
}
