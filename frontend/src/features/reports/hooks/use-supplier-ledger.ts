"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { reportKeys } from "@/features/reports/constants/query-keys";
import { toSupplierLedgerParams } from "@/features/reports/schemas/supplier-ledger-filters";
import type { SupplierLedgerFilters } from "@/features/reports/schemas/supplier-ledger-filters";
import { reportsService } from "@/features/reports/services/reports-service";

/**
 * The Supplier Ledger's server-side, paginated fetch - mirrors
 * `useCustomerLedger` exactly, on the buy side. Stays `enabled: false`
 * until a supplier is picked - `supplier_id` is a required backend param.
 */
export function useSupplierLedger(filters: SupplierLedgerFilters) {
  const params = toSupplierLedgerParams(filters);

  return useQuery({
    queryKey: params ? reportKeys.supplierLedgerResult(params) : reportKeys.supplierLedger(),
    queryFn: () => reportsService.getSupplierLedger(params!),
    enabled: params !== null,
    placeholderData: keepPreviousData,
  });
}
