"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { reportKeys } from "@/features/reports/constants/query-keys";
import { toCustomerLedgerParams } from "@/features/reports/schemas/customer-ledger-filters";
import type { CustomerLedgerFilters } from "@/features/reports/schemas/customer-ledger-filters";
import { reportsService } from "@/features/reports/services/reports-service";

/**
 * The Customer Ledger's server-side, paginated fetch — every filter/page
 * change refetches from the backend rather than filtering an already-loaded
 * page client-side (mirrors `useInvoices`). Stays `enabled: false` until a
 * customer is picked - `customer_id` is a required backend param, so there
 * is nothing to fetch before then. `keepPreviousData` keeps the current
 * rows on screen while a filter/page change is in flight.
 */
export function useCustomerLedger(filters: CustomerLedgerFilters) {
  const params = toCustomerLedgerParams(filters);

  return useQuery({
    queryKey: params ? reportKeys.customerLedgerResult(params) : reportKeys.customerLedger(),
    queryFn: () => reportsService.getCustomerLedger(params!),
    enabled: params !== null,
    placeholderData: keepPreviousData,
  });
}
