/** Mirrors the backend's SupplierPaymentStatus enum (app/modules/supplier_payments/constants.py). */
export type SupplierPaymentStatus = "draft" | "posted" | "cancelled";

/** Mirrors the backend's PaymentMethod enum (app/modules/supplier_payments/constants.py). */
export type SupplierPaymentMethod = "cash" | "upi" | "cheque" | "bank_transfer" | "card" | "adjustment";

/**
 * Raw backend shape (snake_case), matching SupplierPaymentResponse
 * (app/modules/supplier_payments/schemas.py) exactly. Every money field is a
 * string - the backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1), and the client keeps that representation rather
 * than parsing into a JS number. There is no nested `supplier` object here -
 * `supplier_id` is the only reference the backend returns, mirroring
 * `BackendPayment`'s own `company_id`-only shape. There is no nested
 * `allocations` array either - allocations are a separate sub-resource
 * (`GET /supplier-payments/{id}/allocations`), out of this session's scope.
 */
export interface BackendSupplierPayment {
  id: string;
  tenant_id: string;
  supplier_id: string;
  payment_number: string | null;
  payment_date: string;
  payment_method: SupplierPaymentMethod;
  reference_number: string | null;
  bank_name: string | null;
  amount: string;
  allocated_amount: string;
  unallocated_amount: string;
  remarks: string | null;
  status: SupplierPaymentStatus;
  posted_at: string | null;
  created_at: string;
  updated_at: string;
}

/** The client-facing, camelCase shape every supplier-payment-service.ts function returns. */
export interface SupplierPayment {
  id: string;
  tenantId: string;
  supplierId: string;
  paymentNumber: string | null;
  paymentDate: string;
  paymentMethod: SupplierPaymentMethod;
  referenceNumber: string | null;
  bankName: string | null;
  amount: string;
  allocatedAmount: string;
  unallocatedAmount: string;
  remarks: string | null;
  status: SupplierPaymentStatus;
  postedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export function mapBackendSupplierPayment(payment: BackendSupplierPayment): SupplierPayment {
  return {
    id: payment.id,
    tenantId: payment.tenant_id,
    supplierId: payment.supplier_id,
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
    postedAt: payment.posted_at,
    createdAt: payment.created_at,
    updatedAt: payment.updated_at,
  };
}

/**
 * Request body for POST /supplier-payments (SupplierPaymentCreateRequest,
 * app/modules/supplier_payments/schemas.py) - snake_case to match the wire
 * format exactly. `supplier_id`, `payment_date`, `payment_method` and
 * `amount` are required; every other field is optional.
 * `payment_number`, `allocated_amount`, `unallocated_amount`, `status` and
 * `posted_at` are not accepted here at all - the server always owns them:
 * number stays NULL until posting (a later session), allocated_amount
 * starts at 0, unallocated_amount starts equal to `amount`, and status is
 * always DRAFT.
 */
export interface SupplierPaymentCreateRequest {
  supplier_id: string;
  payment_date: string;
  payment_method: SupplierPaymentMethod;
  reference_number?: string;
  bank_name?: string;
  amount: string;
  remarks?: string;
}

/**
 * Request body for PUT /supplier-payments/{id} (SupplierPaymentUpdateRequest)
 * - a partial update, only present fields change. Only `draft` supplier
 * payments may be updated (409 `SUPPLIER_PAYMENT_NOT_DRAFT` otherwise -
 * posted/cancelled payments are immutable, see
 * app/modules/supplier_payments/service.py's `_ensure_draft`).
 */
export type SupplierPaymentUpdateRequest = Partial<SupplierPaymentCreateRequest>;

/**
 * Query params for GET /supplier-payments (app/modules/supplier_payments/
 * schemas.py's SupplierPaymentListParams) - snake_case to match the wire
 * format exactly, since `supplier-payment-service.ts` forwards these
 * straight through as a query string. `payment_date_from`/`payment_date_to`
 * are supported by the backend but not yet wired to a UI control - the same
 * deferral `PaymentListParams` made for its own date range.
 */
export interface SupplierPaymentListParams {
  q?: string;
  status?: SupplierPaymentStatus;
  supplier_id?: string;
  payment_method?: SupplierPaymentMethod;
  payment_date_from?: string;
  payment_date_to?: string;
  sort: string;
  page: number;
  page_size: number;
}
