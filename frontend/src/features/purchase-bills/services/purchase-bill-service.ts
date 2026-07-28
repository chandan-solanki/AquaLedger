import { bffClient } from "@/lib/bff-client";
import type { ApiListEnvelope } from "@/types/api";
import type {
  BackendPurchaseBill,
  PurchaseBill,
  PurchaseBillCreateRequest,
  PurchaseBillListParams,
  PurchaseBillUpdateRequest,
} from "@/features/purchase-bills/types/purchase-bill";
import { mapBackendPurchaseBill } from "@/features/purchase-bills/types/purchase-bill";

export interface PurchaseBillListResult {
  data: PurchaseBill[];
  meta: ApiListEnvelope<BackendPurchaseBill>["meta"];
}

function buildQueryString(params: PurchaseBillListParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.status) query.set("status", params.status);
  if (params.supplier_id) query.set("supplier_id", params.supplier_id);
  if (params.bill_date_from) query.set("bill_date_from", params.bill_date_from);
  if (params.bill_date_to) query.set("bill_date_to", params.bill_date_to);
  query.set("sort", params.sort);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/purchase/*`) - never the
 * FastAPI backend directly, mirroring `invoice-service.ts`: the browser
 * never holds a bearer token to attach here (ARCHITECTURE.md §1.2, §8.1).
 * The BFF route handlers (`app/api/purchase/**`) attach the caller's
 * HttpOnly access token server-side and forward the request. This is
 * List/Get/Create/Update - line items live in their own
 * `purchase-bill-item-service.ts`, mirroring `invoice-service.ts`/
 * `invoice-item-service.ts`'s own split. Delete/Post are not wired up yet -
 * out of this pass's scope.
 */
export const purchaseBillService = {
  async listPurchaseBills(params: PurchaseBillListParams): Promise<PurchaseBillListResult> {
    const { data } = await bffClient.get<ApiListEnvelope<BackendPurchaseBill>>(
      `/purchase?${buildQueryString(params)}`
    );
    return { data: data.data.map(mapBackendPurchaseBill), meta: data.meta };
  },

  async getPurchaseBill(id: string): Promise<PurchaseBill> {
    const { data } = await bffClient.get<BackendPurchaseBill>(`/purchase/${id}`);
    return mapBackendPurchaseBill(data);
  },

  async createPurchaseBill(payload: PurchaseBillCreateRequest): Promise<PurchaseBill> {
    const { data } = await bffClient.post<BackendPurchaseBill>("/purchase", payload);
    return mapBackendPurchaseBill(data);
  },

  async updatePurchaseBill(id: string, payload: PurchaseBillUpdateRequest): Promise<PurchaseBill> {
    const { data } = await bffClient.put<BackendPurchaseBill>(`/purchase/${id}`, payload);
    return mapBackendPurchaseBill(data);
  },

  /**
   * `draft` -> `posted` (app/modules/purchase/service.py's
   * `PurchaseService.post`) - assigns `bill_number`, recalculates all
   * totals from the bill's current items, and increases the billing
   * supplier's `outstanding_amount` by `balance_amount`, all server-side in
   * one transaction. Takes no request body.
   */
  async postPurchaseBill(id: string): Promise<PurchaseBill> {
    const { data } = await bffClient.post<BackendPurchaseBill>(`/purchase/${id}/post`);
    return mapBackendPurchaseBill(data);
  },
};
