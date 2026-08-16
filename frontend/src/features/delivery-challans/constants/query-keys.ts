import type { DeliveryChallanListParams } from "@/features/delivery-challans/types/delivery-challan";

export const deliveryChallanKeys = {
  all: () => ["delivery-challans"] as const,
  lists: () => [...deliveryChallanKeys.all(), "list"] as const,
  list: (params: DeliveryChallanListParams) => [...deliveryChallanKeys.lists(), params] as const,
  details: () => [...deliveryChallanKeys.all(), "detail"] as const,
  detail: (id: string) => [...deliveryChallanKeys.details(), id] as const,
};

/**
 * Delivery challan items are only ever listed one way - every item on one
 * delivery challan (`GET /delivery-challans/{id}/items`, no pagination) - so
 * this has a single `byChallan` entry rather than the fuller `list(params)`
 * shape `deliveryChallanKeys` needs for its filterable List page, mirroring
 * `purchaseOrderItemKeys`'s `byOrder` shape.
 */
export const deliveryChallanItemKeys = {
  all: () => ["delivery-challan-items"] as const,
  byChallan: (deliveryChallanId: string) =>
    [...deliveryChallanItemKeys.all(), "challan", deliveryChallanId] as const,
};
