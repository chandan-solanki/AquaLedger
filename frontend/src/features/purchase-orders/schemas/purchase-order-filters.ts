import type { PurchaseOrderListParams, PurchaseOrderStatus } from "@/features/purchase-orders/types/purchase-order";

/** Matches the backend's `_SORTABLE_FIELDS` (app/modules/purchase_orders/schemas.py) exactly. */
export const PURCHASE_ORDER_SORT_FIELDS = ["order_date", "po_number", "created_at"] as const;
export type PurchaseOrderSortField = (typeof PURCHASE_ORDER_SORT_FIELDS)[number];

export const PURCHASE_ORDER_SORT_DIRECTIONS = ["asc", "desc"] as const;
export type PurchaseOrderSortDirection = (typeof PURCHASE_ORDER_SORT_DIRECTIONS)[number];

/**
 * `sort`/`direction` are kept separate here (rather than the backend's
 * combined `-field` string) since each is its own URL search param,
 * mirroring `PurchaseBillFilters` - `toPurchaseOrderListParams` recombines
 * them into the wire format the backend actually expects. `supplier` holds
 * a `supplier_id` (selected via the Supplier filter's dropdown, not free
 * text). `orderDateFrom`/`orderDateTo` are ISO date strings (`yyyy-MM-dd`)
 * kept as plain strings in the URL, converted to/from `Date` only at the
 * `DateRangeFilter` component boundary.
 */
export interface PurchaseOrderFilters {
  search: string;
  status: PurchaseOrderStatus | null;
  supplier: string | null;
  orderDateFrom: string | null;
  orderDateTo: string | null;
  page: number;
  pageSize: number;
  sort: PurchaseOrderSortField;
  direction: PurchaseOrderSortDirection;
}

export const DEFAULT_PURCHASE_ORDER_FILTERS: PurchaseOrderFilters = {
  search: "",
  status: null,
  supplier: null,
  orderDateFrom: null,
  orderDateTo: null,
  page: 1,
  pageSize: 20,
  sort: "created_at",
  direction: "desc",
};

/** Maps the client's filter state onto the backend's PurchaseOrderListParams query shape. */
export function toPurchaseOrderListParams(filters: PurchaseOrderFilters): PurchaseOrderListParams {
  return {
    q: filters.search.trim() || undefined,
    status: filters.status ?? undefined,
    supplier_id: filters.supplier ?? undefined,
    order_date_from: filters.orderDateFrom ?? undefined,
    order_date_to: filters.orderDateTo ?? undefined,
    sort: filters.direction === "desc" ? `-${filters.sort}` : filters.sort,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
