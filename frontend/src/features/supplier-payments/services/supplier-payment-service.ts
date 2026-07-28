import { bffClient } from "@/lib/bff-client";
import type { ApiListEnvelope } from "@/types/api";
import type {
  BackendSupplierPayment,
  SupplierPayment,
  SupplierPaymentCreateRequest,
  SupplierPaymentListParams,
  SupplierPaymentUpdateRequest,
} from "@/features/supplier-payments/types/supplier-payment";
import { mapBackendSupplierPayment } from "@/features/supplier-payments/types/supplier-payment";

export interface SupplierPaymentListResult {
  data: SupplierPayment[];
  meta: ApiListEnvelope<BackendSupplierPayment>["meta"];
}

function buildQueryString(params: SupplierPaymentListParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.status) query.set("status", params.status);
  if (params.supplier_id) query.set("supplier_id", params.supplier_id);
  if (params.payment_method) query.set("payment_method", params.payment_method);
  if (params.payment_date_from) query.set("payment_date_from", params.payment_date_from);
  if (params.payment_date_to) query.set("payment_date_to", params.payment_date_to);
  query.set("sort", params.sort);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/supplier-payments/*`) -
 * never the FastAPI backend directly, mirroring `payment-service.ts`: the
 * browser never holds a bearer token to attach here (ARCHITECTURE.md §1.2,
 * §8.1). The BFF route handlers (`app/api/supplier-payments/**`) attach the
 * caller's HttpOnly access token server-side and forward the request. This
 * is List/Get/Create/Update/Delete/Post (Sprint 9 Sessions 1-4) - Cancel/
 * Refund remain out of scope: the backend exposes no such endpoints
 * (app/modules/supplier_payments/router.py has exactly ten routes;
 * `SupplierPaymentStatus.CANCELLED` exists in the enum but nothing
 * transitions a payment to it).
 */
export const supplierPaymentService = {
  async listSupplierPayments(params: SupplierPaymentListParams): Promise<SupplierPaymentListResult> {
    const { data } = await bffClient.get<ApiListEnvelope<BackendSupplierPayment>>(
      `/supplier-payments?${buildQueryString(params)}`
    );
    return { data: data.data.map(mapBackendSupplierPayment), meta: data.meta };
  },

  async getSupplierPayment(id: string): Promise<SupplierPayment> {
    const { data } = await bffClient.get<BackendSupplierPayment>(`/supplier-payments/${id}`);
    return mapBackendSupplierPayment(data);
  },

  async createSupplierPayment(payload: SupplierPaymentCreateRequest): Promise<SupplierPayment> {
    const { data } = await bffClient.post<BackendSupplierPayment>("/supplier-payments", payload);
    return mapBackendSupplierPayment(data);
  },

  async updateSupplierPayment(
    id: string,
    payload: SupplierPaymentUpdateRequest
  ): Promise<SupplierPayment> {
    const { data } = await bffClient.put<BackendSupplierPayment>(`/supplier-payments/${id}`, payload);
    return mapBackendSupplierPayment(data);
  },

  async deleteSupplierPayment(id: string): Promise<void> {
    await bffClient.delete(`/supplier-payments/${id}`);
  },

  /**
   * `draft` -> `posted` (app/modules/supplier_payments/service.py's
   * `SupplierPaymentService.post`) - assigns `payment_number` and locks the
   * payment as immutable, all server-side in one transaction. Takes no
   * request body - the backend recomputes everything from the payment's own
   * current allocations. Purchase bill/supplier balances are untouched by
   * this call (already kept correct by every allocation mutation made while
   * this payment was draft).
   */
  async postSupplierPayment(id: string): Promise<SupplierPayment> {
    const { data } = await bffClient.post<BackendSupplierPayment>(`/supplier-payments/${id}/post`);
    return mapBackendSupplierPayment(data);
  },
};
