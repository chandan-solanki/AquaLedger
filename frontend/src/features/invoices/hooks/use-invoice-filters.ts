"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import { INVOICE_STATUS_VALUES } from "@/features/invoices/constants/invoice-status";
import {
  DEFAULT_INVOICE_FILTERS,
  INVOICE_SORT_DIRECTIONS,
  INVOICE_SORT_FIELDS,
} from "@/features/invoices/schemas/invoice-filters";

const invoiceFilterParsers = {
  search: parseAsString.withDefault(DEFAULT_INVOICE_FILTERS.search),
  status: parseAsStringEnum([...INVOICE_STATUS_VALUES]),
  company: parseAsString,
  page: parseAsInteger.withDefault(DEFAULT_INVOICE_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_INVOICE_FILTERS.pageSize),
  sort: parseAsStringEnum([...INVOICE_SORT_FIELDS]).withDefault(DEFAULT_INVOICE_FILTERS.sort),
  direction: parseAsStringEnum([...INVOICE_SORT_DIRECTIONS]).withDefault(DEFAULT_INVOICE_FILTERS.direction),
};

/**
 * Invoice list filter/sort/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10: "URL/filter state: nuqs... non-negotiable for list
 * screens users share"), mirroring `useTripFilters` exactly.
 */
export function useInvoiceFilters() {
  return useQueryStates(invoiceFilterParsers, { history: "push" });
}
