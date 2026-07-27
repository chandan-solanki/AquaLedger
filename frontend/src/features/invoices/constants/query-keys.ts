import type { InvoiceListParams } from "@/features/invoices/types/invoice";

export const invoiceKeys = {
  all: () => ["invoices"] as const,
  lists: () => [...invoiceKeys.all(), "list"] as const,
  list: (params: InvoiceListParams) => [...invoiceKeys.lists(), params] as const,
  details: () => [...invoiceKeys.all(), "detail"] as const,
  detail: (id: string) => [...invoiceKeys.details(), id] as const,
};

/**
 * Invoice items are only ever listed one way - every non-deleted item on
 * one invoice (`GET /invoices/{invoice_id}/items`, no pagination) - so this
 * has a single `byInvoice` entry rather than the fuller `list(params)`
 * shape `invoiceKeys` needs for its filterable List page, mirroring
 * `tripCatchKeys`/`tripExpenseKeys`'s `byTrip` shape.
 */
export const invoiceItemKeys = {
  all: () => ["invoice-items"] as const,
  byInvoice: (invoiceId: string) => [...invoiceItemKeys.all(), "invoice", invoiceId] as const,
};
