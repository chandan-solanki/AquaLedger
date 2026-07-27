import type { InvoiceListParams, InvoiceStatus } from "@/features/invoices/types/invoice";

/** Matches the backend's `_SORTABLE_FIELDS` (app/modules/invoices/schemas.py) exactly. */
export const INVOICE_SORT_FIELDS = ["invoice_date", "invoice_number", "created_at"] as const;
export type InvoiceSortField = (typeof INVOICE_SORT_FIELDS)[number];

export const INVOICE_SORT_DIRECTIONS = ["asc", "desc"] as const;
export type InvoiceSortDirection = (typeof INVOICE_SORT_DIRECTIONS)[number];

/**
 * `sort`/`direction` are kept separate here (rather than the backend's
 * combined `-field` string) since each is its own URL search param,
 * mirroring `TripFilters` - `toInvoiceListParams` recombines them into the
 * wire format the backend actually expects. `company` holds a `company_id`
 * (selected via the Company filter's dropdown, not free text), mirroring
 * `TripFilters.boat`.
 */
export interface InvoiceFilters {
  search: string;
  status: InvoiceStatus | null;
  company: string | null;
  page: number;
  pageSize: number;
  sort: InvoiceSortField;
  direction: InvoiceSortDirection;
}

export const DEFAULT_INVOICE_FILTERS: InvoiceFilters = {
  search: "",
  status: null,
  company: null,
  page: 1,
  pageSize: 20,
  sort: "created_at",
  direction: "desc",
};

/** Maps the client's filter state onto the backend's InvoiceListParams query shape. */
export function toInvoiceListParams(filters: InvoiceFilters): InvoiceListParams {
  return {
    q: filters.search.trim() || undefined,
    status: filters.status ?? undefined,
    company_id: filters.company ?? undefined,
    sort: filters.direction === "desc" ? `-${filters.sort}` : filters.sort,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
