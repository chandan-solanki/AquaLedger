"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import type { ComboboxOption } from "@/components/form";
import { invoiceKeys, invoiceService, useCompanyOptions } from "@/features/invoices";
import type { Invoice, InvoiceListParams } from "@/features/invoices";
import { formatCurrency } from "@/utils/format-currency";

const INVOICE_OPTIONS_PARAMS: InvoiceListParams = { sort: "-invoice_date", page: 1, page_size: 100 };

const _DELIVERABLE_STATUSES: ReadonlySet<Invoice["status"]> = new Set([
  "issued",
  "partially_paid",
  "paid",
]);

/**
 * All invoices for this tenant (most recent first, capped at 100 - the same
 * bounded-options posture `useSupplierOptions`/`useCompanyOptions` take),
 * for resolving `invoice_id` to a display label across this feature:
 * `invoiceById` backs the List page's Invoice column/filter,
 * `eligibleOptions` backs the Create page's Invoice picker.
 *
 * The backend's `GET /invoices` list endpoint has no "deliverable" filter
 * (app/modules/invoices/schemas.py's `InvoiceListParams` only supports a
 * single `status` value, not a set) and delivery_challans' own Session 14
 * scope deliberately added no new invoices-module endpoint for this - so
 * `eligibleOptions` fetches the plain unfiltered list and applies the
 * ISSUED/PARTIALLY_PAID/PAID narrowing client-side, the minimum-safe-UI-
 * filtering fallback this session's own brief calls for. The backend
 * remains the actual authority: `DeliveryChallanService._validate_invoice_link`
 * re-checks the same statuses server-side on every create.
 */
export function useInvoiceOptions() {
  const invoicesQuery = useQuery({
    queryKey: invoiceKeys.list(INVOICE_OPTIONS_PARAMS),
    queryFn: () => invoiceService.listInvoices(INVOICE_OPTIONS_PARAMS),
    staleTime: 5 * 60 * 1000,
  });
  const companyOptions = useCompanyOptions();

  const invoices = invoicesQuery.data?.data;
  const isLoading = invoicesQuery.isLoading || companyOptions.isLoading;

  return useMemo(() => {
    const list = invoices ?? [];
    const invoiceById = new Map(list.map((invoice) => [invoice.id, invoice]));
    const eligibleOptions: ComboboxOption[] = list
      .filter((invoice) => _DELIVERABLE_STATUSES.has(invoice.status))
      .map((invoice) => {
        const companyName = companyOptions.nameById.get(invoice.companyId) ?? "Unknown customer";
        const number = invoice.invoiceNumber ?? "Draft";
        return {
          value: invoice.id,
          label: `${number} — ${companyName} (Balance: ${formatCurrency(invoice.balanceAmount)})`,
        };
      });

    return { invoiceById, companyNameById: companyOptions.nameById, eligibleOptions, isLoading };
  }, [invoices, companyOptions.nameById, isLoading]);
}
