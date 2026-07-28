/**
 * Raw backend shape (snake_case), matching SupplierPaymentAllocationResponse
 * (app/modules/supplier_payments/schemas.py) exactly. `allocated_amount` is
 * a string - the backend serializes `Decimal` as a JSON string, never a
 * float (ARCHITECTURE.md §5.1). There is no nested `purchase_bill` object
 * here - `purchase_bill_id` is the only reference the backend returns, so
 * the referenced bill's own fields (number, date, total, balance) are
 * resolved separately (see `supplier-payment-allocation-table.tsx`), never
 * joined server-side or duplicated here. There is also no `updated_at` -
 * `SupplierPaymentAllocation` is append-only/hard-deleted, not
 * `TimestampMixin`-based like `SupplierPayment` itself (see the model's own
 * docstring).
 */
export interface BackendSupplierPaymentAllocation {
  id: string;
  tenant_id: string;
  supplier_payment_id: string;
  purchase_bill_id: string;
  allocated_amount: string;
  created_at: string;
}

/** The client-facing, camelCase shape every supplier-payment-allocation-service.ts function returns. */
export interface SupplierPaymentAllocation {
  id: string;
  tenantId: string;
  supplierPaymentId: string;
  purchaseBillId: string;
  allocatedAmount: string;
  createdAt: string;
}

export function mapBackendSupplierPaymentAllocation(
  allocation: BackendSupplierPaymentAllocation
): SupplierPaymentAllocation {
  return {
    id: allocation.id,
    tenantId: allocation.tenant_id,
    supplierPaymentId: allocation.supplier_payment_id,
    purchaseBillId: allocation.purchase_bill_id,
    allocatedAmount: allocation.allocated_amount,
    createdAt: allocation.created_at,
  };
}

/**
 * Request body for POST /supplier-payments/{supplier_payment_id}/allocations
 * (SupplierPaymentAllocationCreateRequest, app/modules/supplier_payments/
 * schemas.py) - snake_case to match the wire format exactly.
 * `allocated_amount` must be positive; the backend additionally validates it
 * against the purchase bill's current `balance_amount` and the payment's
 * current `unallocated_amount` (422 `SUPPLIER_PAYMENT_ALLOCATION_AMOUNT_EXCEEDED`
 * otherwise) - left server-validated only, mirroring how
 * `PaymentAllocationCreateRequest` leaves the same pair of ceilings server-
 * validated.
 */
export interface SupplierPaymentAllocationCreateRequest {
  purchase_bill_id: string;
  allocated_amount: string;
}

/**
 * Request body for PUT /supplier-payments/{supplier_payment_id}/allocations/
 * {allocation_id} (SupplierPaymentAllocationUpdateRequest) - a partial
 * update, only present fields change. Only allocations on `draft` supplier
 * payments may be updated (409
 * `SUPPLIER_PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT` otherwise).
 */
export type SupplierPaymentAllocationUpdateRequest = Partial<SupplierPaymentAllocationCreateRequest>;
