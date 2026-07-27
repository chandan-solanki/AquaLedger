"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { invoiceKeys } from "@/features/invoices/constants/query-keys";
import type { InvoiceFilters } from "@/features/invoices/schemas/invoice-filters";
import { toInvoiceListParams } from "@/features/invoices/schemas/invoice-filters";
import { invoiceService } from "@/features/invoices/services/invoice-service";

/**
 * Server-side, paginated invoice list — every filter/sort/page change
 * refetches from the backend rather than filtering an already-loaded page
 * client-side, mirroring `useBoats`/`useTrips`. `keepPreviousData` keeps the
 * current rows on screen (instead of flashing to a loading state) while a
 * filter/page change is in flight.
 */
export function useInvoices(filters: InvoiceFilters) {
  const params = toInvoiceListParams(filters);

  return useQuery({
    queryKey: invoiceKeys.list(params),
    queryFn: () => invoiceService.listInvoices(params),
    placeholderData: keepPreviousData,
  });
}
