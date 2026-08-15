"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import {
  DEFAULT_CUSTOMER_LEDGER_FILTERS,
  TRANSACTION_TYPE_VALUES,
} from "@/features/reports/schemas/customer-ledger-filters";

const customerLedgerFilterParsers = {
  customerId: parseAsString,
  fromDate: parseAsString,
  toDate: parseAsString,
  transactionType: parseAsStringEnum([...TRANSACTION_TYPE_VALUES]),
  page: parseAsInteger.withDefault(DEFAULT_CUSTOMER_LEDGER_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_CUSTOMER_LEDGER_FILTERS.pageSize),
};

/**
 * Customer Ledger filter/sort/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10: "URL/filter state: nuqs... non-negotiable for list
 * screens users share"), mirroring `useInvoiceFilters`.
 */
export function useCustomerLedgerFilters() {
  return useQueryStates(customerLedgerFilterParsers, { history: "push" });
}
