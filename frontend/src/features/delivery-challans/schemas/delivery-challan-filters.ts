import type {
  DeliveryChallanListParams,
  DeliveryChallanStatus,
} from "@/features/delivery-challans/types/delivery-challan";

/** Matches the backend's `_SORTABLE_FIELDS` (app/modules/delivery_challans/schemas.py) exactly. */
export const DELIVERY_CHALLAN_SORT_FIELDS = ["challan_date", "challan_number", "created_at"] as const;
export type DeliveryChallanSortField = (typeof DELIVERY_CHALLAN_SORT_FIELDS)[number];

export const DELIVERY_CHALLAN_SORT_DIRECTIONS = ["asc", "desc"] as const;
export type DeliveryChallanSortDirection = (typeof DELIVERY_CHALLAN_SORT_DIRECTIONS)[number];

/**
 * `sort`/`direction` are kept separate here (rather than the backend's
 * combined `-field` string) since each is its own URL search param,
 * mirroring `PurchaseOrderFilters` - `toDeliveryChallanListParams`
 * recombines them into the wire format the backend actually expects.
 * `invoice` holds an `invoice_id` (selected via the Invoice filter's
 * dropdown, not free text). There is deliberately no `customer` filter -
 * the backend exposes no company/customer filter on this list endpoint (the
 * customer is only ever reachable via the linked invoice).
 */
export interface DeliveryChallanFilters {
  search: string;
  status: DeliveryChallanStatus | null;
  invoice: string | null;
  challanDateFrom: string | null;
  challanDateTo: string | null;
  page: number;
  pageSize: number;
  sort: DeliveryChallanSortField;
  direction: DeliveryChallanSortDirection;
}

export const DEFAULT_DELIVERY_CHALLAN_FILTERS: DeliveryChallanFilters = {
  search: "",
  status: null,
  invoice: null,
  challanDateFrom: null,
  challanDateTo: null,
  page: 1,
  pageSize: 20,
  sort: "created_at",
  direction: "desc",
};

/** Maps the client's filter state onto the backend's DeliveryChallanListParams query shape. */
export function toDeliveryChallanListParams(filters: DeliveryChallanFilters): DeliveryChallanListParams {
  return {
    q: filters.search.trim() || undefined,
    status: filters.status ?? undefined,
    invoice_id: filters.invoice ?? undefined,
    challan_date_from: filters.challanDateFrom ?? undefined,
    challan_date_to: filters.challanDateTo ?? undefined,
    sort: filters.direction === "desc" ? `-${filters.sort}` : filters.sort,
    page: filters.page,
    page_size: filters.pageSize,
  };
}
