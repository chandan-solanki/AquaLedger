"use client";

import { useQuery } from "@tanstack/react-query";

import { purchaseOrderLinkedBillKeys } from "@/features/purchase-orders/constants/query-keys";
import { purchaseOrderService } from "@/features/purchase-orders/services/purchase-order-service";

/**
 * Every Purchase Bill linked to one purchase order (Sprint 12 Session 13) -
 * disabled until a purchase order id is available. No pagination
 * (`GET /purchase-orders/{id}/purchase-bills` returns a plain array), the
 * same posture `usePurchaseOrderItems` takes.
 */
export function usePurchaseOrderLinkedBills(purchaseOrderId: string | undefined) {
  return useQuery({
    queryKey: purchaseOrderLinkedBillKeys.byOrder(purchaseOrderId ?? ""),
    queryFn: () => purchaseOrderService.listLinkedPurchaseBills(purchaseOrderId as string),
    enabled: Boolean(purchaseOrderId),
  });
}
