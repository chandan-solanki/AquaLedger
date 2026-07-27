/**
 * Raw backend shape (snake_case), matching InvoiceItemResponse
 * (app/modules/invoices/schemas.py) exactly. Every money/quantity/rate
 * field is a string - the backend serializes `Decimal` as a JSON string,
 * never a float (ARCHITECTURE.md §5.1). `discount_amount`/`taxable_amount`/
 * `tax_amount`/`line_total` are always server-computed - never accepted on
 * create/update, only ever read here.
 */
export interface BackendInvoiceItem {
  id: string;
  tenant_id: string;
  invoice_id: string;
  line_number: number;
  fish_id: string;
  trip_catch_id: string | null;
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

/** The client-facing, camelCase shape every invoice-item-service.ts function returns. */
export interface InvoiceItem {
  id: string;
  tenantId: string;
  invoiceId: string;
  lineNumber: number;
  fishId: string;
  tripCatchId: string | null;
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

export function mapBackendInvoiceItem(item: BackendInvoiceItem): InvoiceItem {
  return {
    id: item.id,
    tenantId: item.tenant_id,
    invoiceId: item.invoice_id,
    lineNumber: item.line_number,
    fishId: item.fish_id,
    tripCatchId: item.trip_catch_id,
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
 * Query params for GET /invoices/{invoice_id}/items - no pagination (the
 * backend returns a plain array, not a paginated envelope: "an invoice's
 * line count is small and bounded," app/modules/invoices/router.py). `q`
 * searches the item's description and the sold fish's name.
 */
export interface InvoiceItemListParams {
  q?: string;
}

/**
 * Request body for POST /invoices/{invoice_id}/items (InvoiceItemCreateRequest,
 * app/modules/invoices/schemas.py) - snake_case to match the wire format
 * exactly. `trip_catch_id` and `fish_id` are both required - the trip
 * catch's fish must match `fish_id` (422 otherwise), and `quantity` must
 * not exceed the trip catch's available_quantity (422 otherwise), both
 * validated server-side. Financial fields (discount_amount/taxable_amount/
 * tax_amount/line_total) are never accepted - the server always owns them.
 */
export interface InvoiceItemCreateRequest {
  trip_catch_id: string;
  fish_id: string;
  description?: string;
  quantity: string;
  unit: string;
  rate: string;
  discount_percent?: string;
  tax_rate?: string;
}

/**
 * Request body for PUT /invoices/{invoice_id}/items/{item_id}
 * (InvoiceItemUpdateRequest) - a partial update, only present fields
 * change. Only items on `draft` invoices may be updated (409
 * `INVOICE_NOT_DRAFT` otherwise, app/modules/invoices/service.py's
 * `_ensure_draft`).
 */
export type InvoiceItemUpdateRequest = Partial<InvoiceItemCreateRequest>;
