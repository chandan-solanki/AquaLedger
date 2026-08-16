import { bffClient } from "@/lib/bff-client";
import type {
  BackendDeliveryChallanItem,
  DeliveryChallanItem,
  DeliveryChallanItemCreateRequest,
  DeliveryChallanItemUpdateRequest,
} from "@/features/delivery-challans/types/delivery-challan-item";
import { mapBackendDeliveryChallanItem } from "@/features/delivery-challans/types/delivery-challan-item";

/**
 * Talks only to the Next.js BFF's own routes
 * (`/api/delivery-challans/{id}/items*`) - never the FastAPI backend
 * directly, mirroring `purchase-order-item-service.ts`. `listDeliveryChallanItems`
 * returns a plain array, not a paginated envelope - the backend itself
 * returns `list[DeliveryChallanItemResponse]`, not `PaginatedResponse[...]`
 * (a challan's line count is small and bounded).
 */
export const deliveryChallanItemService = {
  async listDeliveryChallanItems(deliveryChallanId: string): Promise<DeliveryChallanItem[]> {
    const { data } = await bffClient.get<BackendDeliveryChallanItem[]>(
      `/delivery-challans/${deliveryChallanId}/items`
    );
    return data.map(mapBackendDeliveryChallanItem);
  },

  async createDeliveryChallanItem(
    deliveryChallanId: string,
    payload: DeliveryChallanItemCreateRequest
  ): Promise<DeliveryChallanItem> {
    const { data } = await bffClient.post<BackendDeliveryChallanItem>(
      `/delivery-challans/${deliveryChallanId}/items`,
      payload
    );
    return mapBackendDeliveryChallanItem(data);
  },

  async updateDeliveryChallanItem(
    deliveryChallanId: string,
    itemId: string,
    payload: DeliveryChallanItemUpdateRequest
  ): Promise<DeliveryChallanItem> {
    const { data } = await bffClient.put<BackendDeliveryChallanItem>(
      `/delivery-challans/${deliveryChallanId}/items/${itemId}`,
      payload
    );
    return mapBackendDeliveryChallanItem(data);
  },

  async deleteDeliveryChallanItem(deliveryChallanId: string, itemId: string): Promise<void> {
    await bffClient.delete(`/delivery-challans/${deliveryChallanId}/items/${itemId}`);
  },
};
