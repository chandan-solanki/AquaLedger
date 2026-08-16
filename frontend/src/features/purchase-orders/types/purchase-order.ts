/** Mirrors the backend's PurchaseOrderStatus enum (app/modules/purchase_orders/constants.py). */
export type PurchaseOrderStatus = "draft" | "confirmed" | "fulfilled" | "cancelled";

/**
 * Mirrors the backend's PurchaseOrderBillingStatus enum
 * (app/modules/purchase_orders/constants.py) - derived, never stored;
 * distinct from `PurchaseOrderStatus` (a CONFIRMED order can be
 * FULLY_BILLED and stay CONFIRMED - billing never drives fulfillment).
 */
export type PurchaseOrderBillingStatus = "not_billed" | "partially_billed" | "fully_billed";

/**
 * Raw backend shape (snake_case), matching PurchaseOrderResponse
 * (app/modules/purchase_orders/schemas.py) exactly. Every money field is a
 * string - the backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1). There is no nested `items` array here - line
 * items are a separate sub-resource (`GET /purchase-orders/{id}/items`).
 *
 * Unlike `BackendPurchaseBill`, there is no `paid_amount`/`balance_amount` -
 * a purchase order is never paid (it is a procurement commitment, not a
 * bill); those columns belong to PurchaseBill only.
 *
 * `billed_amount`/`remaining_amount`/`billing_status` (Sprint 12 Session 12)
 * are only ever present on the single-`GET /purchase-orders/{id}` response
 * (`PurchaseOrderDetailResponse` on the backend) - list/create/update/
 * confirm/cancel/fulfill all return the plain response without them, so
 * they're typed optional here rather than always-present.
 */
export interface BackendPurchaseOrder {
  id: string;
  tenant_id: string;
  supplier_id: string;
  po_number: string | null;
  order_date: string;
  expected_delivery_date: string | null;
  status: PurchaseOrderStatus;
  subtotal: string;
  discount_amount: string;
  taxable_amount: string;
  tax_amount: string;
  transport_charge: string;
  other_charge: string;
  round_off: string;
  total_amount: string;
  remarks: string | null;
  confirmed_at: string | null;
  created_at: string;
  updated_at: string;
  billed_amount?: string;
  remaining_amount?: string;
  billing_status?: PurchaseOrderBillingStatus;
}

/** The client-facing, camelCase shape every purchase-order-service.ts function returns. */
export interface PurchaseOrder {
  id: string;
  tenantId: string;
  supplierId: string;
  poNumber: string | null;
  orderDate: string;
  expectedDeliveryDate: string | null;
  status: PurchaseOrderStatus;
  subtotal: string;
  discountAmount: string;
  taxableAmount: string;
  taxAmount: string;
  transportCharge: string;
  otherCharge: string;
  roundOff: string;
  totalAmount: string;
  remarks: string | null;
  confirmedAt: string | null;
  createdAt: string;
  updatedAt: string;
  billedAmount?: string;
  remainingAmount?: string;
  billingStatus?: PurchaseOrderBillingStatus;
}

export function mapBackendPurchaseOrder(order: BackendPurchaseOrder): PurchaseOrder {
  return {
    id: order.id,
    tenantId: order.tenant_id,
    supplierId: order.supplier_id,
    poNumber: order.po_number,
    orderDate: order.order_date,
    expectedDeliveryDate: order.expected_delivery_date,
    status: order.status,
    subtotal: order.subtotal,
    discountAmount: order.discount_amount,
    taxableAmount: order.taxable_amount,
    taxAmount: order.tax_amount,
    transportCharge: order.transport_charge,
    otherCharge: order.other_charge,
    roundOff: order.round_off,
    totalAmount: order.total_amount,
    remarks: order.remarks,
    confirmedAt: order.confirmed_at,
    createdAt: order.created_at,
    updatedAt: order.updated_at,
    billedAmount: order.billed_amount,
    remainingAmount: order.remaining_amount,
    billingStatus: order.billing_status,
  };
}

/**
 * Query params for GET /purchase-orders (app/modules/purchase_orders/
 * schemas.py's PurchaseOrderListParams) - snake_case to match the wire
 * format exactly, since `purchase-order-service.ts` forwards these straight
 * through as a query string.
 */
export interface PurchaseOrderListParams {
  q?: string;
  status?: PurchaseOrderStatus;
  supplier_id?: string;
  /** If true, restrict to CONFIRMED/FULFILLED orders - the set eligible for Purchase Bill linkage. */
  billable?: boolean;
  order_date_from?: string;
  order_date_to?: string;
  sort: string;
  page: number;
  page_size: number;
}

/**
 * Request body for POST /purchase-orders (PurchaseOrderCreateRequest,
 * app/modules/purchase_orders/schemas.py) - snake_case to match the wire
 * format exactly. `supplier_id` and `order_date` are required;
 * `expected_delivery_date`/`remarks` are optional. Every financial field
 * (subtotal/discount_amount/taxable_amount/tax_amount/transport_charge/
 * other_charge/round_off/total_amount) starts at 0 and is server-owned,
 * computed once line items exist. `po_number`/`status`/`confirmed_at` are
 * never client-supplied either - numbers are assigned only at confirm.
 */
export interface PurchaseOrderCreateRequest {
  supplier_id: string;
  order_date: string;
  expected_delivery_date?: string;
  remarks?: string;
}

/**
 * Request body for PUT /purchase-orders/{id} (PurchaseOrderUpdateRequest) -
 * a partial update, only present fields change. Only `draft` purchase
 * orders may be updated (409 `PURCHASE_ORDER_NOT_DRAFT` otherwise -
 * confirmed/fulfilled/cancelled orders are immutable, see
 * app/modules/purchase_orders/service.py's `_ensure_draft`).
 */
export type PurchaseOrderUpdateRequest = Partial<PurchaseOrderCreateRequest>;
