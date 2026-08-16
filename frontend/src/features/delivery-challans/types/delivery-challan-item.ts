/**
 * Raw backend shape (snake_case), matching DeliveryChallanItemResponse
 * (app/modules/delivery_challans/schemas.py) exactly. A delivery challan
 * item carries no financial fields at all (no rate/tax/discount/line_total)
 * - it is a pure quantity record against a specific invoice item, never a
 * priced line. `unit` is a server-derived snapshot of the linked invoice
 * item's own unit at creation time - never client-supplied.
 */
export interface BackendDeliveryChallanItem {
  id: string;
  tenant_id: string;
  delivery_challan_id: string;
  invoice_item_id: string;
  line_number: number;
  quantity: string;
  unit: string;
  created_at: string;
  updated_at: string;
}

/** The client-facing, camelCase shape every delivery-challan-item-service.ts function returns. */
export interface DeliveryChallanItem {
  id: string;
  tenantId: string;
  deliveryChallanId: string;
  invoiceItemId: string;
  lineNumber: number;
  quantity: string;
  unit: string;
  createdAt: string;
  updatedAt: string;
}

export function mapBackendDeliveryChallanItem(item: BackendDeliveryChallanItem): DeliveryChallanItem {
  return {
    id: item.id,
    tenantId: item.tenant_id,
    deliveryChallanId: item.delivery_challan_id,
    invoiceItemId: item.invoice_item_id,
    lineNumber: item.line_number,
    quantity: item.quantity,
    unit: item.unit,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  };
}

/**
 * Request body for POST /delivery-challans/{delivery_challan_id}/items
 * (DeliveryChallanItemCreateRequest, app/modules/delivery_challans/schemas.py) -
 * snake_case to match the wire format exactly. `invoice_item_id` must
 * belong to this challan's own linked invoice; `line_number` and `unit` are
 * never client-supplied - both are server-assigned/derived.
 */
export interface DeliveryChallanItemCreateRequest {
  invoice_item_id: string;
  quantity: string;
}

/**
 * Request body for PUT /delivery-challans/{delivery_challan_id}/items/{item_id}
 * (DeliveryChallanItemUpdateRequest) - a partial update, only `quantity` may
 * change. `invoice_item_id` is immutable after creation - not accepted here.
 * Only items on `draft` delivery challans may be updated (409
 * `DELIVERY_CHALLAN_NOT_DRAFT` otherwise).
 */
export interface DeliveryChallanItemUpdateRequest {
  quantity?: string;
}
