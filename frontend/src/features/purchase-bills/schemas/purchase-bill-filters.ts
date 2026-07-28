import type { PurchaseBillListParams, PurchaseBillStatus } from "@/features/purchase-bills/types/purchase-bill";

/** Matches the backend's `_SORTABLE_FIELDS` (app/modules/purchase/schemas.py) exactly. */
export const PURCHASE_BILL_SORT_FIELDS = ["bill_date", "bill_number", "created_at"] as const;
export type PurchaseBillSortField = (typeof PURCHASE_BILL_SORT_FIELDS)[number];

export const PURCHASE_BILL_SORT_DIRECTIONS = ["asc", "desc"] as const;
export type PurchaseBillSortDirection = (typeof PURCHASE_BILL_SORT_DIRECTIONS)[number];

/**
 * `sort`/`direction` are kept separate here (rather than the backend's
 * combined `-field` string) since each is its own URL search param,
 * mirroring `InvoiceFilters` - `toPurchaseBillListParams` recombines them
 * into the wire format the backend actually expects. `supplier` holds a
 * `supplier_id` (selected via the Supplier filter's dropdown, not free
 * text), mirroring `InvoiceFilters.company`. `bill_date_from`/
 * `bill_date_to` are backend-supported but deliberately not wired to a
 * filter control yet, the same deferral `InvoiceFilters` made for its own
 * date range.
 */
export interface PurchaseBillFilters {
  search: string;
  status: PurchaseBillStatus | null;
  supplier: string | null;
  page: number;
  pageSize: number;
  sort: PurchaseBillSortField;
  direction: PurchaseBillSortDirection;
}

export const DEFAULT_PURCHASE_BILL_FILTERS: PurchaseBillFilters = {
  search: "",
  status: null,
  supplier: null,
  page: 1,
  pageSize: 20,
  sort: "created_at",
  direction: "desc",
};

/** Maps the client's filter state onto the backend's PurchaseBillListParams query shape. */
export function toPurchaseBillListParams(filters: PurchaseBillFilters): PurchaseBillListParams {
  return {
    q: filters.search.trim() || undefined,
    status: filters.status ?? undefined,
    supplier_id: filters.supplier ?? undefined,
    sort: filters.direction === "desc" ? `-${filters.sort}` : filters.sort,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
