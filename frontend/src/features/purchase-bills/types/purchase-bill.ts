/** Mirrors the backend's PurchaseStatus enum (app/modules/purchase/constants.py). */
export type PurchaseBillStatus = "draft" | "posted" | "partially_paid" | "paid" | "cancelled";

/**
 * Raw backend shape (snake_case), matching PurchaseBillResponse
 * (app/modules/purchase/schemas.py) exactly. Every money field is a string -
 * the backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1). There is no nested `items` array here - line
 * items are a separate sub-resource (`GET /purchase/{id}/items`).
 */
export interface BackendPurchaseBill {
  id: string;
  tenant_id: string;
  supplier_id: string;
  bill_number: string | null;
  bill_date: string;
  due_date: string | null;
  status: PurchaseBillStatus;
  subtotal: string;
  discount_amount: string;
  taxable_amount: string;
  tax_amount: string;
  transport_charge: string;
  other_charge: string;
  round_off: string;
  total_amount: string;
  paid_amount: string;
  balance_amount: string;
  remarks: string | null;
  posted_at: string | null;
  created_at: string;
  updated_at: string;
}

/** The client-facing, camelCase shape every purchase-bill-service.ts function returns. */
export interface PurchaseBill {
  id: string;
  tenantId: string;
  supplierId: string;
  billNumber: string | null;
  billDate: string;
  dueDate: string | null;
  status: PurchaseBillStatus;
  subtotal: string;
  discountAmount: string;
  taxableAmount: string;
  taxAmount: string;
  transportCharge: string;
  otherCharge: string;
  roundOff: string;
  totalAmount: string;
  paidAmount: string;
  balanceAmount: string;
  remarks: string | null;
  postedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export function mapBackendPurchaseBill(bill: BackendPurchaseBill): PurchaseBill {
  return {
    id: bill.id,
    tenantId: bill.tenant_id,
    supplierId: bill.supplier_id,
    billNumber: bill.bill_number,
    billDate: bill.bill_date,
    dueDate: bill.due_date,
    status: bill.status,
    subtotal: bill.subtotal,
    discountAmount: bill.discount_amount,
    taxableAmount: bill.taxable_amount,
    taxAmount: bill.tax_amount,
    transportCharge: bill.transport_charge,
    otherCharge: bill.other_charge,
    roundOff: bill.round_off,
    totalAmount: bill.total_amount,
    paidAmount: bill.paid_amount,
    balanceAmount: bill.balance_amount,
    remarks: bill.remarks,
    postedAt: bill.posted_at,
    createdAt: bill.created_at,
    updatedAt: bill.updated_at,
  };
}

/**
 * Query params for GET /purchase (app/modules/purchase/schemas.py's
 * PurchaseBillListParams) - snake_case to match the wire format exactly,
 * since `purchase-bill-service.ts` forwards these straight through as a
 * query string. `bill_date_from`/`bill_date_to` are backend-supported but
 * deliberately not wired to a filter control yet, the same deferral
 * `InvoiceListParams` made for `invoice_date_from`/`invoice_date_to`.
 */
export interface PurchaseBillListParams {
  q?: string;
  status?: PurchaseBillStatus;
  supplier_id?: string;
  bill_date_from?: string;
  bill_date_to?: string;
  sort: string;
  page: number;
  page_size: number;
}

/**
 * Request body for POST /purchase (PurchaseBillCreateRequest,
 * app/modules/purchase/schemas.py) - snake_case to match the wire format
 * exactly. `supplier_id` and `bill_date` are required; `due_date`/`remarks`
 * are optional. Unlike `InvoiceCreateRequest`, `transport_charge`/
 * `other_charge` are NOT accepted here at all - every financial field
 * (subtotal/discount_amount/taxable_amount/tax_amount/transport_charge/
 * other_charge/round_off/total_amount/paid_amount/balance_amount) starts at
 * 0 and is server-owned, computed once line items exist. `bill_number`/
 * `status`/`posted_at` are never client-supplied either - numbers are
 * assigned only at posting (not yet wired up on this frontend).
 */
export interface PurchaseBillCreateRequest {
  supplier_id: string;
  bill_date: string;
  due_date?: string;
  remarks?: string;
}

/**
 * Request body for PUT /purchase/{id} (PurchaseBillUpdateRequest) - a
 * partial update, only present fields change. Only `draft` purchase bills
 * may be updated (409 `PURCHASE_BILL_NOT_DRAFT` otherwise - posted/
 * partially_paid/paid/cancelled bills are immutable, see
 * app/modules/purchase/service.py's `_ensure_draft`).
 */
export type PurchaseBillUpdateRequest = Partial<PurchaseBillCreateRequest>;
