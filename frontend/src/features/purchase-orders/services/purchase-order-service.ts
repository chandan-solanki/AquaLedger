import { bffClient } from "@/lib/bff-client";
import type { ApiListEnvelope } from "@/types/api";
import type {
  BackendPurchaseOrder,
  PurchaseOrder,
  PurchaseOrderCreateRequest,
  PurchaseOrderListParams,
  PurchaseOrderUpdateRequest,
} from "@/features/purchase-orders/types/purchase-order";
import { mapBackendPurchaseOrder } from "@/features/purchase-orders/types/purchase-order";
import type {
  BackendPurchaseOrderLinkedBill,
  PurchaseOrderLinkedBill,
} from "@/features/purchase-orders/types/purchase-order-linked-bill";
import { mapBackendPurchaseOrderLinkedBill } from "@/features/purchase-orders/types/purchase-order-linked-bill";

export interface PurchaseOrderListResult {
  data: PurchaseOrder[];
  meta: ApiListEnvelope<BackendPurchaseOrder>["meta"];
}

function buildQueryString(params: PurchaseOrderListParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.status) query.set("status", params.status);
  if (params.supplier_id) query.set("supplier_id", params.supplier_id);
  if (params.billable) query.set("billable", "true");
  if (params.order_date_from) query.set("order_date_from", params.order_date_from);
  if (params.order_date_to) query.set("order_date_to", params.order_date_to);
  query.set("sort", params.sort);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/purchase-orders/*`) -
 * never the FastAPI backend directly, mirroring `purchase-bill-service.ts`:
 * the browser never holds a bearer token to attach here (ARCHITECTURE.md
 * §1.2, §8.1). The BFF route handlers (`app/api/purchase-orders/**`) attach
 * the caller's HttpOnly access token server-side and forward the request.
 * Line items live in their own `purchase-order-item-service.ts`.
 *
 * `confirmPurchaseOrder`/`cancelPurchaseOrder`/`fulfillPurchaseOrder` are
 * the three lifecycle transitions - unlike `postPurchaseBill`, none of them
 * has any effect on supplier outstanding/ledger (a purchase order is a
 * procurement commitment, not a bill; verified in
 * app/modules/purchase_orders/router.py's own docstrings).
 */
export const purchaseOrderService = {
  async listPurchaseOrders(params: PurchaseOrderListParams): Promise<PurchaseOrderListResult> {
    const { data } = await bffClient.get<ApiListEnvelope<BackendPurchaseOrder>>(
      `/purchase-orders?${buildQueryString(params)}`
    );
    return { data: data.data.map(mapBackendPurchaseOrder), meta: data.meta };
  },

  async getPurchaseOrder(id: string): Promise<PurchaseOrder> {
    const { data } = await bffClient.get<BackendPurchaseOrder>(`/purchase-orders/${id}`);
    return mapBackendPurchaseOrder(data);
  },

  async createPurchaseOrder(payload: PurchaseOrderCreateRequest): Promise<PurchaseOrder> {
    const { data } = await bffClient.post<BackendPurchaseOrder>("/purchase-orders", payload);
    return mapBackendPurchaseOrder(data);
  },

  async updatePurchaseOrder(id: string, payload: PurchaseOrderUpdateRequest): Promise<PurchaseOrder> {
    const { data } = await bffClient.put<BackendPurchaseOrder>(`/purchase-orders/${id}`, payload);
    return mapBackendPurchaseOrder(data);
  },

  async deletePurchaseOrder(id: string): Promise<void> {
    await bffClient.delete(`/purchase-orders/${id}`);
  },

  /**
   * `draft` -> `confirmed` (app/modules/purchase_orders/service.py's
   * `PurchaseOrderService.confirm`) - assigns `po_number` and recalculates
   * all totals from the order's current items, server-side in one
   * transaction. Takes no request body. Never touches supplier outstanding.
   */
  async confirmPurchaseOrder(id: string): Promise<PurchaseOrder> {
    const { data } = await bffClient.post<BackendPurchaseOrder>(`/purchase-orders/${id}/confirm`);
    return mapBackendPurchaseOrder(data);
  },

  /** `draft`|`confirmed` -> `cancelled`. No side effects on any other module. */
  async cancelPurchaseOrder(id: string): Promise<PurchaseOrder> {
    const { data } = await bffClient.post<BackendPurchaseOrder>(`/purchase-orders/${id}/cancel`);
    return mapBackendPurchaseOrder(data);
  },

  /** `confirmed` -> `fulfilled`. No side effects on any other module. */
  async fulfillPurchaseOrder(id: string): Promise<PurchaseOrder> {
    const { data } = await bffClient.post<BackendPurchaseOrder>(`/purchase-orders/${id}/fulfill`);
    return mapBackendPurchaseOrder(data);
  },

  /**
   * Every Purchase Bill linked to this purchase order (Sprint 12 Session
   * 13), most recent bill_date first. A plain array, not a paginated
   * envelope - a purchase order's bill count is small and bounded, the same
   * posture `listPurchaseOrderItems` takes.
   */
  async listLinkedPurchaseBills(id: string): Promise<PurchaseOrderLinkedBill[]> {
    const { data } = await bffClient.get<BackendPurchaseOrderLinkedBill[]>(
      `/purchase-orders/${id}/purchase-bills`
    );
    return data.map(mapBackendPurchaseOrderLinkedBill);
  },
};
