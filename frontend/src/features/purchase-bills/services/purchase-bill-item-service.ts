import { bffClient } from "@/lib/bff-client";
import type {
  BackendPurchaseBillItem,
  PurchaseBillItem,
  PurchaseBillItemCreateRequest,
  PurchaseBillItemUpdateRequest,
} from "@/features/purchase-bills/types/purchase-bill-item";
import { mapBackendPurchaseBillItem } from "@/features/purchase-bills/types/purchase-bill-item";

/**
 * Talks only to the Next.js BFF's own routes
 * (`/api/purchase/{id}/items*`) - never the FastAPI backend directly,
 * mirroring `invoice-item-service.ts`. `listPurchaseBillItems` returns a
 * plain array, not a paginated envelope - the backend itself returns
 * `list[PurchaseBillItemResponse]`, not `PaginatedResponse[...]`
 * (app/modules/purchase/router.py: "a bill's line count is small and
 * bounded").
 */
export const purchaseBillItemService = {
  async listPurchaseBillItems(purchaseBillId: string): Promise<PurchaseBillItem[]> {
    const { data } = await bffClient.get<BackendPurchaseBillItem[]>(`/purchase/${purchaseBillId}/items`);
    return data.map(mapBackendPurchaseBillItem);
  },

  async createPurchaseBillItem(
    purchaseBillId: string,
    payload: PurchaseBillItemCreateRequest
  ): Promise<PurchaseBillItem> {
    const { data } = await bffClient.post<BackendPurchaseBillItem>(
      `/purchase/${purchaseBillId}/items`,
      payload
    );
    return mapBackendPurchaseBillItem(data);
  },

  async updatePurchaseBillItem(
    purchaseBillId: string,
    itemId: string,
    payload: PurchaseBillItemUpdateRequest
  ): Promise<PurchaseBillItem> {
    const { data } = await bffClient.put<BackendPurchaseBillItem>(
      `/purchase/${purchaseBillId}/items/${itemId}`,
      payload
    );
    return mapBackendPurchaseBillItem(data);
  },

  async deletePurchaseBillItem(purchaseBillId: string, itemId: string): Promise<void> {
    await bffClient.delete(`/purchase/${purchaseBillId}/items/${itemId}`);
  },
};
