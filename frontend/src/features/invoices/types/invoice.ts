/** Mirrors the backend's InvoiceStatus enum (app/modules/invoices/constants.py). */
export type InvoiceStatus = "draft" | "issued" | "partially_paid" | "paid" | "cancelled";

/**
 * Raw backend shape (snake_case), matching InvoiceResponse
 * (app/modules/invoices/schemas.py) exactly. Every money field is a string -
 * the backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1), and the client keeps that representation rather
 * than parsing into a JS number. There is no nested `items` array here -
 * line items are a separate sub-resource (`GET /invoices/{id}/items`), out
 * of this session's scope (see TASKS.md).
 */
export interface BackendInvoice {
  id: string;
  tenant_id: string;
  company_id: string;
  invoice_number: string | null;
  invoice_date: string;
  due_date: string | null;
  status: InvoiceStatus;
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
  issued_at: string | null;
  created_at: string;
  updated_at: string;
}

/** The client-facing, camelCase shape every invoice-service.ts function returns. */
export interface Invoice {
  id: string;
  tenantId: string;
  companyId: string;
  invoiceNumber: string | null;
  invoiceDate: string;
  dueDate: string | null;
  status: InvoiceStatus;
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
  issuedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export function mapBackendInvoice(invoice: BackendInvoice): Invoice {
  return {
    id: invoice.id,
    tenantId: invoice.tenant_id,
    companyId: invoice.company_id,
    invoiceNumber: invoice.invoice_number,
    invoiceDate: invoice.invoice_date,
    dueDate: invoice.due_date,
    status: invoice.status,
    subtotal: invoice.subtotal,
    discountAmount: invoice.discount_amount,
    taxableAmount: invoice.taxable_amount,
    taxAmount: invoice.tax_amount,
    transportCharge: invoice.transport_charge,
    otherCharge: invoice.other_charge,
    roundOff: invoice.round_off,
    totalAmount: invoice.total_amount,
    paidAmount: invoice.paid_amount,
    balanceAmount: invoice.balance_amount,
    remarks: invoice.remarks,
    issuedAt: invoice.issued_at,
    createdAt: invoice.created_at,
    updatedAt: invoice.updated_at,
  };
}

/**
 * Query params for GET /invoices (app/modules/invoices/schemas.py's
 * InvoiceListParams) - snake_case to match the wire format exactly, since
 * `invoice-service.ts` forwards these straight through as a query string.
 * Only `q`/`status`/`company_id`/`sort`/`page`/`page_size` are wired to UI
 * controls this session (see `toInvoiceListParams`); the
 * `invoice_date_from`/`invoice_date_to` range filters the backend already
 * supports are left for a later session's filter panel, the same deferral
 * `TripListParams`'s `trip_type`/date-range filters made in Sprint 5.
 */
export interface InvoiceListParams {
  q?: string;
  status?: InvoiceStatus;
  company_id?: string;
  invoice_date_from?: string;
  invoice_date_to?: string;
  sort: string;
  page: number;
  page_size: number;
}

/**
 * Request body for POST /invoices (InvoiceCreateRequest,
 * app/modules/invoices/schemas.py) - snake_case to match the wire format
 * exactly. `company_id` and `invoice_date` are required; every other field
 * the backend defaults or accepts as null when omitted. `transport_charge`/
 * `other_charge` are the only financial inputs the client controls - every
 * *calculated* field (subtotal/discount_amount/taxable_amount/tax_amount/
 * total_amount/paid_amount/balance_amount) is computed server-side and not
 * accepted here at all. `status` is always DRAFT and `invoice_number`
 * always NULL at creation - neither is client-supplied; numbers are
 * assigned only at issue (Sprint 7 Session 3+ scope).
 */
export interface InvoiceCreateRequest {
  company_id: string;
  invoice_date: string;
  due_date?: string;
  transport_charge?: string;
  other_charge?: string;
  remarks?: string;
}

/**
 * Request body for PUT /invoices/{id} (InvoiceUpdateRequest) - a partial
 * update, only present fields change. Only `draft` invoices may be updated
 * (409 `INVOICE_NOT_DRAFT` otherwise - issued/paid/cancelled invoices are
 * immutable, see app/modules/invoices/service.py's `_ensure_draft`).
 */
export type InvoiceUpdateRequest = Partial<InvoiceCreateRequest>;
