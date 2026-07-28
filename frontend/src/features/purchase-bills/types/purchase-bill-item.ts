/**
 * Raw backend shape (snake_case), matching PurchaseBillItemResponse
 * (app/modules/purchase/schemas.py) exactly. Every money/quantity/rate field
 * is a string - the backend serializes `Decimal` as a JSON string, never a
 * float (ARCHITECTURE.md §5.1). `discount_amount`/`taxable_amount`/
 * `tax_amount`/`line_total` are always server-computed. Unlike
 * `InvoiceItem`, there is no `fish_id`/`trip_catch_id` - a purchase line has
 * no link to a sold-fish master or a trip catch (app/modules/purchase/
 * schemas.py's `PurchaseBillItemCreateRequest` docstring).
 */
export interface BackendPurchaseBillItem {
  id: string;
  tenant_id: string;
  purchase_bill_id: string;
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
}

/** The client-facing, camelCase shape every purchase-bill-service.ts item function returns. */
export interface PurchaseBillItem {
  id: string;
  tenantId: string;
  purchaseBillId: string;
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
}

export function mapBackendPurchaseBillItem(item: BackendPurchaseBillItem): PurchaseBillItem {
  return {
    id: item.id,
    tenantId: item.tenant_id,
    purchaseBillId: item.purchase_bill_id,
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
  };
}

/**
 * Request body for POST /purchase/{purchase_bill_id}/items
 * (PurchaseBillItemCreateRequest, app/modules/purchase/schemas.py) -
 * snake_case to match the wire format exactly. Unlike
 * `InvoiceItemCreateRequest`, `description` is required here (even though
 * the underlying column stays nullable) and there is no `fish_id`/
 * `trip_catch_id` - a purchase line has no link to a sold-fish master or a
 * trip catch. Financial fields (discount_amount/taxable_amount/tax_amount/
 * line_total) are never accepted - the server always owns them.
 */
export interface PurchaseBillItemCreateRequest {
  description: string;
  quantity: string;
  unit: string;
  rate: string;
  discount_percent?: string;
  tax_rate?: string;
}

/**
 * Request body for PUT /purchase/{purchase_bill_id}/items/{item_id}
 * (PurchaseBillItemUpdateRequest) - a partial update, only present fields
 * change. Only items on `draft` purchase bills may be updated (409
 * `PURCHASE_BILL_NOT_DRAFT` otherwise, app/modules/purchase/service.py's
 * `_ensure_draft`).
 */
export type PurchaseBillItemUpdateRequest = Partial<PurchaseBillItemCreateRequest>;
