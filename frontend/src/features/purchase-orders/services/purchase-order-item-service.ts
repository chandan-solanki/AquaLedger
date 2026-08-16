import { bffClient } from "@/lib/bff-client";
import type {
  BackendPurchaseOrderItem,
  PurchaseOrderItem,
  PurchaseOrderItemCreateRequest,
  PurchaseOrderItemUpdateRequest,
} from "@/features/purchase-orders/types/purchase-order-item";
import { mapBackendPurchaseOrderItem } from "@/features/purchase-orders/types/purchase-order-item";

/**
 * Talks only to the Next.js BFF's own routes
 * (`/api/purchase-orders/{id}/items*`) - never the FastAPI backend
 * directly, mirroring `purchase-bill-item-service.ts`. `listPurchaseOrderItems`
 * returns a plain array, not a paginated envelope - the backend itself
 * returns `list[PurchaseOrderItemResponse]`, not `PaginatedResponse[...]`
 * (an order's line count is small and bounded).
 */
export const purchaseOrderItemService = {
  async listPurchaseOrderItems(purchaseOrderId: string): Promise<PurchaseOrderItem[]> {
    const { data } = await bffClient.get<BackendPurchaseOrderItem[]>(
      `/purchase-orders/${purchaseOrderId}/items`
    );
    return data.map(mapBackendPurchaseOrderItem);
  },

  async createPurchaseOrderItem(
    purchaseOrderId: string,
    payload: PurchaseOrderItemCreateRequest
  ): Promise<PurchaseOrderItem> {
    const { data } = await bffClient.post<BackendPurchaseOrderItem>(
      `/purchase-orders/${purchaseOrderId}/items`,
      payload
    );
    return mapBackendPurchaseOrderItem(data);
  },

  async updatePurchaseOrderItem(
    purchaseOrderId: string,
    itemId: string,
    payload: PurchaseOrderItemUpdateRequest
  ): Promise<PurchaseOrderItem> {
    const { data } = await bffClient.put<BackendPurchaseOrderItem>(
      `/purchase-orders/${purchaseOrderId}/items/${itemId}`,
      payload
    );
    return mapBackendPurchaseOrderItem(data);
  },

  async deletePurchaseOrderItem(purchaseOrderId: string, itemId: string): Promise<void> {
    await bffClient.delete(`/purchase-orders/${purchaseOrderId}/items/${itemId}`);
  },
};
