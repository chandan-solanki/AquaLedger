/**
 * Raw backend shape (snake_case), matching PaymentAllocationResponse
 * (app/modules/payments/schemas.py) exactly. `allocated_amount` is a string -
 * the backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1). There is no nested `invoice` object here -
 * `invoice_id` is the only reference the backend returns, so the referenced
 * invoice's own fields (number, date, total, balance) are resolved
 * separately through the Invoices feature's own public API (see
 * `payment-allocation-table.tsx`), never joined server-side or duplicated
 * here. There is also no `updated_at` - `PaymentAllocation` is append-only/
 * hard-deleted, not `TimestampMixin`-based like `Payment` itself (see the
 * model's own docstring).
 */
export interface BackendPaymentAllocation {
  id: string;
  tenant_id: string;
  payment_id: string;
  invoice_id: string;
  allocated_amount: string;
  created_at: string;
}

/** The client-facing, camelCase shape every payment-allocation-service.ts function returns. */
export interface PaymentAllocation {
  id: string;
  tenantId: string;
  paymentId: string;
  invoiceId: string;
  allocatedAmount: string;
  createdAt: string;
}

export function mapBackendPaymentAllocation(allocation: BackendPaymentAllocation): PaymentAllocation {
  return {
    id: allocation.id,
    tenantId: allocation.tenant_id,
    paymentId: allocation.payment_id,
    invoiceId: allocation.invoice_id,
    allocatedAmount: allocation.allocated_amount,
    createdAt: allocation.created_at,
  };
}

/**
 * Request body for POST /payments/{payment_id}/allocations
 * (PaymentAllocationCreateRequest, app/modules/payments/schemas.py) -
 * snake_case to match the wire format exactly. `allocated_amount` must be
 * positive; the backend additionally validates it against the invoice's
 * current `balance_amount` and the payment's current `unallocated_amount`
 * (422 `PAYMENT_ALLOCATION_AMOUNT_EXCEEDED` otherwise) - left server-
 * validated only, mirroring how `InvoiceItemForm` leaves "quantity exceeds
 * available_quantity" server-validated.
 */
export interface PaymentAllocationCreateRequest {
  invoice_id: string;
  allocated_amount: string;
}

/**
 * Request body for PUT /payments/{payment_id}/allocations/{allocation_id}
 * (PaymentAllocationUpdateRequest) - a partial update, only present fields
 * change. Only allocations on `draft` payments may be updated (409
 * `PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT` otherwise).
 */
export type PaymentAllocationUpdateRequest = Partial<PaymentAllocationCreateRequest>;
