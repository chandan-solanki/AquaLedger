/**
 * Raw backend shape (snake_case), matching PurchaseOrderLinkedBillResponse
 * (app/modules/purchase_orders/schemas.py, Sprint 12 Session 13) exactly.
 * Every money field is a string - the backend serializes `Decimal` as a JSON
 * string, never a float (ARCHITECTURE.md §5.1). `status` is the Purchase
 * Bill's own status string (draft/posted/partially_paid/paid/cancelled),
 * reused as-is by the UI via `purchase-bills`' own status labels/badges.
 */
export interface BackendPurchaseOrderLinkedBill {
  id: string;
  bill_number: string | null;
  bill_date: string;
  status: string;
  total_amount: string;
  balance_amount: string;
}

/** The client-facing, camelCase shape `purchase-order-service.ts` returns. */
export interface PurchaseOrderLinkedBill {
  id: string;
  billNumber: string | null;
  billDate: string;
  status: string;
  totalAmount: string;
  balanceAmount: string;
}

export function mapBackendPurchaseOrderLinkedBill(
  bill: BackendPurchaseOrderLinkedBill
): PurchaseOrderLinkedBill {
  return {
    id: bill.id,
    billNumber: bill.bill_number,
    billDate: bill.bill_date,
    status: bill.status,
    totalAmount: bill.total_amount,
    balanceAmount: bill.balance_amount,
  };
}
