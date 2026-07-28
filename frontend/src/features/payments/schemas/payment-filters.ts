import type {
  PaymentListParams,
  PaymentMethod,
  PaymentStatus,
} from "@/features/payments/types/payment";

/** Matches the backend's `_SORTABLE_FIELDS` (app/modules/payments/schemas.py) exactly. */
export const PAYMENT_SORT_FIELDS = ["payment_date", "payment_number", "amount", "created_at"] as const;
export type PaymentSortField = (typeof PAYMENT_SORT_FIELDS)[number];

export const PAYMENT_SORT_DIRECTIONS = ["asc", "desc"] as const;
export type PaymentSortDirection = (typeof PAYMENT_SORT_DIRECTIONS)[number];

/**
 * `sort`/`direction` are kept separate here (rather than the backend's
 * combined `-field` string) since each is its own URL search param,
 * mirroring `InvoiceFilters` - `toPaymentListParams` recombines them into
 * the wire format the backend actually expects. `company` holds a
 * `company_id` (selected via the Company filter's dropdown, not free text),
 * mirroring `InvoiceFilters.company`. `payment_date_from`/`payment_date_to`
 * are backend-supported but deliberately not wired to a filter control yet -
 * the same deferral `InvoiceFilters` made for `invoice_date_from`/
 * `invoice_date_to`; still outstanding as of Sprint 8 Session 5's audit (see
 * frontend/README.md's Payment Module section).
 */
export interface PaymentFilters {
  search: string;
  status: PaymentStatus | null;
  company: string | null;
  method: PaymentMethod | null;
  page: number;
  pageSize: number;
  sort: PaymentSortField;
  direction: PaymentSortDirection;
}

export const DEFAULT_PAYMENT_FILTERS: PaymentFilters = {
  search: "",
  status: null,
  company: null,
  method: null,
  page: 1,
  pageSize: 20,
  sort: "created_at",
  direction: "desc",
};

/** Maps the client's filter state onto the backend's PaymentListParams query shape. */
export function toPaymentListParams(filters: PaymentFilters): PaymentListParams {
  return {
    q: filters.search.trim() || undefined,
    status: filters.status ?? undefined,
    company_id: filters.company ?? undefined,
    payment_method: filters.method ?? undefined,
    sort: filters.direction === "desc" ? `-${filters.sort}` : filters.sort,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
