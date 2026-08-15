"use client";

import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import {
  DEFAULT_SUPPLIER_LEDGER_FILTERS,
  SUPPLIER_TRANSACTION_TYPE_VALUES,
} from "@/features/reports/schemas/supplier-ledger-filters";

const supplierLedgerFilterParsers = {
  supplierId: parseAsString,
  fromDate: parseAsString,
  toDate: parseAsString,
  transactionType: parseAsStringEnum([...SUPPLIER_TRANSACTION_TYPE_VALUES]),
  page: parseAsInteger.withDefault(DEFAULT_SUPPLIER_LEDGER_FILTERS.page),
  pageSize: parseAsInteger.withDefault(DEFAULT_SUPPLIER_LEDGER_FILTERS.pageSize),
};

/**
 * Supplier Ledger filter/sort/page state, synced to the URL via nuqs
 * (ARCHITECTURE.md §10), mirroring `useCustomerLedgerFilters`.
 */
export function useSupplierLedgerFilters() {
  return useQueryStates(supplierLedgerFilterParsers, { history: "push" });
}
