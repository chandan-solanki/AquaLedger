/** Mirrors the backend's PaymentStatus enum (app/modules/payments/constants.py). */
export type PaymentStatus = "draft" | "posted" | "cancelled";

/** Mirrors the backend's PaymentMethod enum (app/modules/payments/constants.py). */
export type PaymentMethod = "cash" | "upi" | "cheque" | "bank_transfer" | "card" | "adjustment";

/**
 * Raw backend shape (snake_case), matching PaymentResponse
 * (app/modules/payments/schemas.py) exactly. Every money field is a string -
 * the backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1), and the client keeps that representation rather
 * than parsing into a JS number. There is no nested `company` object here -
 * `company_id` is the only reference the backend returns (see
 * `use-company-options.ts`), and there is no nested `allocations` array
 * either - allocations are a separate sub-resource
 * (`GET /payments/{id}/allocations`), out of this session's scope (see
 * TASKS.md Sprint 10 Session 1).
 */
export interface BackendPayment {
  id: string;
  tenant_id: string;
  company_id: string;
  payment_number: string | null;
  payment_date: string;
  payment_method: PaymentMethod;
  reference_number: string | null;
  bank_name: string | null;
  amount: string;
  allocated_amount: string;
  unallocated_amount: string;
  remarks: string | null;
  status: PaymentStatus;
  created_at: string;
  updated_at: string;
}

/** The client-facing, camelCase shape every payment-service.ts function returns. */
export interface Payment {
  id: string;
  tenantId: string;
  companyId: string;
  paymentNumber: string | null;
  paymentDate: string;
  paymentMethod: PaymentMethod;
  referenceNumber: string | null;
  bankName: string | null;
  amount: string;
  allocatedAmount: string;
  unallocatedAmount: string;
  remarks: string | null;
  status: PaymentStatus;
  createdAt: string;
  updatedAt: string;
}

export function mapBackendPayment(payment: BackendPayment): Payment {
  return {
    id: payment.id,
    tenantId: payment.tenant_id,
    companyId: payment.company_id,
    paymentNumber: payment.payment_number,
    paymentDate: payment.payment_date,
    paymentMethod: payment.payment_method,
    referenceNumber: payment.reference_number,
    bankName: payment.bank_name,
    amount: payment.amount,
    allocatedAmount: payment.allocated_amount,
    unallocatedAmount: payment.unallocated_amount,
    remarks: payment.remarks,
    status: payment.status,
    createdAt: payment.created_at,
    updatedAt: payment.updated_at,
  };
}

/**
 * Query params for GET /payments (app/modules/payments/schemas.py's
 * PaymentListParams) - snake_case to match the wire format exactly, since
 * `payment-service.ts` forwards these straight through as a query string.
 * `payment_date_from`/`payment_date_to` are supported by the backend but not
 * yet wired to a UI control - deferred to a later session, the same
 * deferral `InvoiceListParams` made for `invoice_date_from`/`invoice_date_to`.
 */
export interface PaymentListParams {
  q?: string;
  status?: PaymentStatus;
  company_id?: string;
  payment_method?: PaymentMethod;
  payment_date_from?: string;
  payment_date_to?: string;
  sort: string;
  page: number;
  page_size: number;
}

/**
 * Request body for POST /payments (PaymentCreateRequest,
 * app/modules/payments/schemas.py) - snake_case to match the wire format
 * exactly. `company_id`, `payment_date`, `payment_method` and `amount` are
 * required; every other field is optional. `payment_number`,
 * `allocated_amount`, `unallocated_amount` and `status` are not accepted
 * here at all - the server always owns them: number stays NULL until
 * posting (a later session), allocated_amount starts at 0,
 * unallocated_amount starts equal to `amount`, and status is always DRAFT.
 */
export interface PaymentCreateRequest {
  company_id: string;
  payment_date: string;
  payment_method: PaymentMethod;
  reference_number?: string;
  bank_name?: string;
  amount: string;
  remarks?: string;
}

/**
 * Request body for PUT /payments/{id} (PaymentUpdateRequest) - a partial
 * update, only present fields change. Only `draft` payments may be updated
 * (409 `PAYMENT_NOT_DRAFT` otherwise - posted/cancelled payments are
 * immutable, see app/modules/payments/service.py's `_ensure_draft`).
 */
export type PaymentUpdateRequest = Partial<PaymentCreateRequest>;
