import type { PurchaseOrderListParams } from "@/features/purchase-orders/types/purchase-order";

export const purchaseOrderKeys = {
  all: () => ["purchase-orders"] as const,
  lists: () => [...purchaseOrderKeys.all(), "list"] as const,
  list: (params: PurchaseOrderListParams) => [...purchaseOrderKeys.lists(), params] as const,
  details: () => [...purchaseOrderKeys.all(), "detail"] as const,
  detail: (id: string) => [...purchaseOrderKeys.details(), id] as const,
};

/**
 * Purchase order items are only ever listed one way - every item on one
 * purchase order (`GET /purchase-orders/{id}/items`, no pagination) - so
 * this has a single `byOrder` entry rather than the fuller `list(params)`
 * shape `purchaseOrderKeys` needs for its filterable List page, mirroring
 * `purchaseBillItemKeys`'s `byBill` shape.
 */
export const purchaseOrderItemKeys = {
  all: () => ["purchase-order-items"] as const,
  byOrder: (purchaseOrderId: string) => [...purchaseOrderItemKeys.all(), "order", purchaseOrderId] as const,
};

/**
 * Purchase Bills linked to one purchase order (Sprint 12 Session 13) - same
 * single "byOrder" shape as `purchaseOrderItemKeys`, since
 * `GET /purchase-orders/{id}/purchase-bills` is likewise unpaginated and
 * scoped to exactly one order.
 */
export const purchaseOrderLinkedBillKeys = {
  all: () => ["purchase-order-linked-bills"] as const,
  byOrder: (purchaseOrderId: string) =>
    [...purchaseOrderLinkedBillKeys.all(), "order", purchaseOrderId] as const,
};
