import type {
  SupplierPaymentListParams,
  SupplierPaymentMethod,
  SupplierPaymentStatus,
} from "@/features/supplier-payments/types/supplier-payment";

/** Matches the backend's `_SORTABLE_FIELDS` (app/modules/supplier_payments/schemas.py) exactly. */
export const SUPPLIER_PAYMENT_SORT_FIELDS = ["payment_date", "payment_number", "created_at"] as const;
export type SupplierPaymentSortField = (typeof SUPPLIER_PAYMENT_SORT_FIELDS)[number];

export const SUPPLIER_PAYMENT_SORT_DIRECTIONS = ["asc", "desc"] as const;
export type SupplierPaymentSortDirection = (typeof SUPPLIER_PAYMENT_SORT_DIRECTIONS)[number];

/**
 * `sort`/`direction` are kept separate here (rather than the backend's
 * combined `-field` string) since each is its own URL search param,
 * mirroring `PaymentFilters` - `toSupplierPaymentListParams` recombines them
 * into the wire format the backend actually expects. `supplier` holds a
 * `supplier_id` (selected via the Supplier filter's dropdown, not free
 * text), mirroring `PaymentFilters.company`. `payment_date_from`/
 * `payment_date_to` are backend-supported but deliberately not wired to a
 * filter control yet, the same deferral `PaymentFilters` made for its own
 * date range.
 */
export interface SupplierPaymentFilters {
  search: string;
  status: SupplierPaymentStatus | null;
  supplier: string | null;
  method: SupplierPaymentMethod | null;
  page: number;
  pageSize: number;
  sort: SupplierPaymentSortField;
  direction: SupplierPaymentSortDirection;
}

export const DEFAULT_SUPPLIER_PAYMENT_FILTERS: SupplierPaymentFilters = {
  search: "",
  status: null,
  supplier: null,
  method: null,
  page: 1,
  pageSize: 20,
  sort: "created_at",
  direction: "desc",
};

/** Maps the client's filter state onto the backend's SupplierPaymentListParams query shape. */
export function toSupplierPaymentListParams(
  filters: SupplierPaymentFilters
): SupplierPaymentListParams {
  return {
    q: filters.search.trim() || undefined,
    status: filters.status ?? undefined,
    supplier_id: filters.supplier ?? undefined,
    payment_method: filters.method ?? undefined,
    sort: filters.direction === "desc" ? `-${filters.sort}` : filters.sort,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
