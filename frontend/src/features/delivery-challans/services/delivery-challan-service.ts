import { bffClient } from "@/lib/bff-client";
import type { ApiListEnvelope } from "@/types/api";
import type {
  BackendDeliveryChallan,
  DeliveryChallan,
  DeliveryChallanCreateRequest,
  DeliveryChallanListParams,
  DeliveryChallanUpdateRequest,
} from "@/features/delivery-challans/types/delivery-challan";
import { mapBackendDeliveryChallan } from "@/features/delivery-challans/types/delivery-challan";

export interface DeliveryChallanListResult {
  data: DeliveryChallan[];
  meta: ApiListEnvelope<BackendDeliveryChallan>["meta"];
}

function buildQueryString(params: DeliveryChallanListParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.status) query.set("status", params.status);
  if (params.invoice_id) query.set("invoice_id", params.invoice_id);
  if (params.challan_date_from) query.set("challan_date_from", params.challan_date_from);
  if (params.challan_date_to) query.set("challan_date_to", params.challan_date_to);
  query.set("sort", params.sort);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/delivery-challans/*`) -
 * never the FastAPI backend directly, mirroring `purchase-order-service.ts`:
 * the browser never holds a bearer token to attach here (ARCHITECTURE.md
 * §1.2, §8.1). The BFF route handlers (`app/api/delivery-challans/**`)
 * attach the caller's HttpOnly access token server-side and forward the
 * request. Line items live in their own `delivery-challan-item-service.ts`.
 *
 * `dispatchDeliveryChallan`/`deliverDeliveryChallan`/`cancelDeliveryChallan`
 * are the three lifecycle transitions - none of them has any effect on
 * customer outstanding, invoice balance, or ledger (verified in
 * app/modules/delivery_challans/router.py's own docstrings) - a delivery
 * challan is a logistics record, not a financial event.
 */
export const deliveryChallanService = {
  async listDeliveryChallans(params: DeliveryChallanListParams): Promise<DeliveryChallanListResult> {
    const { data } = await bffClient.get<ApiListEnvelope<BackendDeliveryChallan>>(
      `/delivery-challans?${buildQueryString(params)}`
    );
    return { data: data.data.map(mapBackendDeliveryChallan), meta: data.meta };
  },

  async getDeliveryChallan(id: string): Promise<DeliveryChallan> {
    const { data } = await bffClient.get<BackendDeliveryChallan>(`/delivery-challans/${id}`);
    return mapBackendDeliveryChallan(data);
  },

  async createDeliveryChallan(payload: DeliveryChallanCreateRequest): Promise<DeliveryChallan> {
    const { data } = await bffClient.post<BackendDeliveryChallan>("/delivery-challans", payload);
    return mapBackendDeliveryChallan(data);
  },

  async updateDeliveryChallan(
    id: string,
    payload: DeliveryChallanUpdateRequest
  ): Promise<DeliveryChallan> {
    const { data } = await bffClient.put<BackendDeliveryChallan>(`/delivery-challans/${id}`, payload);
    return mapBackendDeliveryChallan(data);
  },

  async deleteDeliveryChallan(id: string): Promise<void> {
    await bffClient.delete(`/delivery-challans/${id}`);
  },

  /**
   * `draft` -> `dispatched` (app/modules/delivery_challans/service.py's
   * `DeliveryChallanService.dispatch`) - assigns `challan_number` and stamps
   * `dispatched_at` server-side in one transaction. Takes no request body.
   * Requires at least one item (422 otherwise). Never touches customer
   * outstanding, invoice balance, or ledger.
   */
  async dispatchDeliveryChallan(id: string): Promise<DeliveryChallan> {
    const { data } = await bffClient.post<BackendDeliveryChallan>(`/delivery-challans/${id}/dispatch`);
    return mapBackendDeliveryChallan(data);
  },

  /** `dispatched` -> `delivered` (terminal). No side effects on any other module. */
  async deliverDeliveryChallan(id: string): Promise<DeliveryChallan> {
    const { data } = await bffClient.post<BackendDeliveryChallan>(`/delivery-challans/${id}/deliver`);
    return mapBackendDeliveryChallan(data);
  },

  /** `draft`|`dispatched` -> `cancelled`. No side effects on any other module. */
  async cancelDeliveryChallan(id: string): Promise<DeliveryChallan> {
    const { data } = await bffClient.post<BackendDeliveryChallan>(`/delivery-challans/${id}/cancel`);
    return mapBackendDeliveryChallan(data);
  },
};
