/**
 * Raw backend shape (snake_case), matching PurchaseOrderItemResponse
 * (app/modules/purchase_orders/schemas.py) exactly. Every money/quantity/rate
 * field is a string - the backend serializes `Decimal` as a JSON string,
 * never a float (ARCHITECTURE.md §5.1). `discount_amount`/`taxable_amount`/
 * `tax_amount`/`line_total` are always server-computed. There is no
 * `fish_id`/`trip_catch_id` - a purchase order line has no link to a sold-
 * fish master or a trip catch, mirroring `BackendPurchaseBillItem`.
 *
 * `billed_quantity`/`remaining_quantity` (Sprint 12 Session 12) are derived
 * from linked purchase bill items and only ever present on
 * `GET /purchase-orders/{id}/items` (`PurchaseOrderItemBillingResponse` on
 * the backend) - add/update item responses return the plain shape without
 * them (both are only ever reachable while the parent order is still
 * DRAFT, a state in which nothing could possibly be billed yet), so
 * they're typed optional here.
 */
export interface BackendPurchaseOrderItem {
  id: string;
  tenant_id: string;
  purchase_order_id: string;
  line_number: number;
  description: string | null;
  quantity: string;
  unit: string;
  rate: string;
  discount_percent: string;
  discount_amount: string;
  taxable_amount: string;
  tax_rate: string;
  tax_amount: string;
  line_total: string;
  created_at: string;
  updated_at: string;
  billed_quantity?: string;
  remaining_quantity?: string;
}

/** The client-facing, camelCase shape every purchase-order-service.ts item function returns. */
export interface PurchaseOrderItem {
  id: string;
  tenantId: string;
  purchaseOrderId: string;
  lineNumber: number;
  description: string | null;
  quantity: string;
  unit: string;
  rate: string;
  discountPercent: string;
  discountAmount: string;
  taxableAmount: string;
  taxRate: string;
  taxAmount: string;
  lineTotal: string;
  createdAt: string;
  updatedAt: string;
  billedQuantity?: string;
  remainingQuantity?: string;
}

export function mapBackendPurchaseOrderItem(item: BackendPurchaseOrderItem): PurchaseOrderItem {
  return {
    id: item.id,
    tenantId: item.tenant_id,
    purchaseOrderId: item.purchase_order_id,
    lineNumber: item.line_number,
    description: item.description,
    quantity: item.quantity,
    unit: item.unit,
    rate: item.rate,
    discountPercent: item.discount_percent,
    discountAmount: item.discount_amount,
    taxableAmount: item.taxable_amount,
    taxRate: item.tax_rate,
    taxAmount: item.tax_amount,
    lineTotal: item.line_total,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
    billedQuantity: item.billed_quantity,
    remainingQuantity: item.remaining_quantity,
  };
}

/**
 * Request body for POST /purchase-orders/{purchase_order_id}/items
 * (PurchaseOrderItemCreateRequest, app/modules/purchase_orders/schemas.py) -
 * snake_case to match the wire format exactly. `description` is required
 * (even though the underlying column stays nullable) and there is no
 * `fish_id`/`trip_catch_id`. Financial fields (discount_amount/
 * taxable_amount/tax_amount/line_total) are never accepted - the server
 * always owns them.
 */
export interface PurchaseOrderItemCreateRequest {
  description: string;
  quantity: string;
  unit: string;
  rate: string;
  discount_percent?: string;
  tax_rate?: string;
}

/**
 * Request body for PUT /purchase-orders/{purchase_order_id}/items/{item_id}
 * (PurchaseOrderItemUpdateRequest) - a partial update, only present fields
 * change. Only items on `draft` purchase orders may be updated (409
 * `PURCHASE_ORDER_NOT_DRAFT` otherwise).
 */
export type PurchaseOrderItemUpdateRequest = Partial<PurchaseOrderItemCreateRequest>;
