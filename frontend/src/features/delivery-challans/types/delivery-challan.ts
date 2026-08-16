/** Mirrors the backend's DeliveryChallanStatus enum (app/modules/delivery_challans/constants.py). */
export type DeliveryChallanStatus = "draft" | "dispatched" | "delivered" | "cancelled";

/**
 * Raw backend shape (snake_case), matching DeliveryChallanResponse
 * (app/modules/delivery_challans/schemas.py) exactly. Every quantity field
 * elsewhere in this module is a string - the backend serializes `Decimal`
 * as a JSON string, never a float (ARCHITECTURE.md §5.1). There are
 * deliberately no financial fields here at all (no subtotal/tax/
 * total_amount) - a delivery challan is a logistics document, never a
 * financial one - and no `company_id` either: the customer is always read
 * via the linked invoice (`invoice_id`), never duplicated.
 */
export interface BackendDeliveryChallan {
  id: string;
  tenant_id: string;
  invoice_id: string;
  challan_number: string | null;
  challan_date: string;
  status: DeliveryChallanStatus;
  remarks: string | null;
  dispatched_at: string | null;
  delivered_at: string | null;
  created_at: string;
  updated_at: string;
}

/** The client-facing, camelCase shape every delivery-challan-service.ts function returns. */
export interface DeliveryChallan {
  id: string;
  tenantId: string;
  invoiceId: string;
  challanNumber: string | null;
  challanDate: string;
  status: DeliveryChallanStatus;
  remarks: string | null;
  dispatchedAt: string | null;
  deliveredAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export function mapBackendDeliveryChallan(challan: BackendDeliveryChallan): DeliveryChallan {
  return {
    id: challan.id,
    tenantId: challan.tenant_id,
    invoiceId: challan.invoice_id,
    challanNumber: challan.challan_number,
    challanDate: challan.challan_date,
    status: challan.status,
    remarks: challan.remarks,
    dispatchedAt: challan.dispatched_at,
    deliveredAt: challan.delivered_at,
    createdAt: challan.created_at,
    updatedAt: challan.updated_at,
  };
}

/**
 * Query params for GET /delivery-challans (app/modules/delivery_challans/
 * schemas.py's DeliveryChallanListParams) - snake_case to match the wire
 * format exactly, since `delivery-challan-service.ts` forwards these
 * straight through as a query string. There is deliberately no
 * `company_id`/customer filter - the backend exposes none (the customer is
 * only ever reachable via the linked invoice), so the List page's filter
 * bar offers Invoice, not Customer, per that constraint.
 */
export interface DeliveryChallanListParams {
  q?: string;
  status?: DeliveryChallanStatus;
  invoice_id?: string;
  challan_date_from?: string;
  challan_date_to?: string;
  sort: string;
  page: number;
  page_size: number;
}

/**
 * Request body for POST /delivery-challans (DeliveryChallanCreateRequest,
 * app/modules/delivery_challans/schemas.py) - snake_case to match the wire
 * format exactly. `invoice_id` and `challan_date` are required; `remarks` is
 * optional. `challan_number`/`status`/`dispatched_at`/`delivered_at` are
 * never client-supplied - the server always owns them (status is always
 * DRAFT at creation; the number and timestamps stay NULL until dispatch()/
 * deliver()).
 */
export interface DeliveryChallanCreateRequest {
  invoice_id: string;
  challan_date: string;
  remarks?: string;
}

/**
 * Request body for PUT /delivery-challans/{id} (DeliveryChallanUpdateRequest) -
 * a partial update, only present fields change. Only `draft` delivery
 * challans may be updated (409 `DELIVERY_CHALLAN_NOT_DRAFT` otherwise).
 * `invoice_id` is immutable after creation - not accepted here, unlike
 * `DeliveryChallanCreateRequest`.
 */
export interface DeliveryChallanUpdateRequest {
  challan_date?: string;
  remarks?: string;
}
