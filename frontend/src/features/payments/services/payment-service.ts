import { bffClient } from "@/lib/bff-client";
import type { ApiListEnvelope } from "@/types/api";
import type {
  BackendPayment,
  Payment,
  PaymentCreateRequest,
  PaymentListParams,
  PaymentUpdateRequest,
} from "@/features/payments/types/payment";
import { mapBackendPayment } from "@/features/payments/types/payment";

export interface PaymentListResult {
  data: Payment[];
  meta: ApiListEnvelope<BackendPayment>["meta"];
}

function buildQueryString(params: PaymentListParams): string {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.status) query.set("status", params.status);
  if (params.company_id) query.set("company_id", params.company_id);
  if (params.payment_method) query.set("payment_method", params.payment_method);
  if (params.payment_date_from) query.set("payment_date_from", params.payment_date_from);
  if (params.payment_date_to) query.set("payment_date_to", params.payment_date_to);
  query.set("sort", params.sort);
  query.set("page", String(params.page));
  query.set("page_size", String(params.page_size));
  return query.toString();
}

/**
 * Talks only to the Next.js BFF's own routes (`/api/payments/*`) - never the
 * FastAPI backend directly, mirroring `invoice-service.ts`: the browser
 * never holds a bearer token to attach here (ARCHITECTURE.md §1.2, §8.1).
 * The BFF route handlers (`app/api/payments/**`) attach the caller's HttpOnly
 * access token server-side and forward the request. This is the module's
 * full CRUD + lifecycle surface (Sprint 8 Sessions 1-4): List/Get/Create/
 * Update/Delete/Post. There is no Cancel/Refund method here - the backend
 * exposes no such endpoint (app/modules/payments/router.py has exactly ten
 * routes; `PaymentStatus.CANCELLED` exists in the enum but nothing
 * transitions a payment to it yet).
 */
export const paymentService = {
  async listPayments(params: PaymentListParams): Promise<PaymentListResult> {
    const { data } = await bffClient.get<ApiListEnvelope<BackendPayment>>(
      `/payments?${buildQueryString(params)}`
    );
    return { data: data.data.map(mapBackendPayment), meta: data.meta };
  },

  async getPayment(id: string): Promise<Payment> {
    const { data } = await bffClient.get<BackendPayment>(`/payments/${id}`);
    return mapBackendPayment(data);
  },

  async createPayment(payload: PaymentCreateRequest): Promise<Payment> {
    const { data } = await bffClient.post<BackendPayment>("/payments", payload);
    return mapBackendPayment(data);
  },

  async updatePayment(id: string, payload: PaymentUpdateRequest): Promise<Payment> {
    const { data } = await bffClient.put<BackendPayment>(`/payments/${id}`, payload);
    return mapBackendPayment(data);
  },

  async deletePayment(id: string): Promise<void> {
    await bffClient.delete(`/payments/${id}`);
  },

  /**
   * `draft` -> `posted` (app/modules/payments/service.py's `PaymentService.post`)
   * - assigns `payment_number` and locks the payment as immutable, all
   * server-side in one transaction. Takes no request body - the backend
   * recomputes everything from the payment's own current allocations.
   * Invoice/Company balances are untouched by this call (already kept
   * correct by every allocation mutation while the payment was draft).
   */
  async postPayment(id: string): Promise<Payment> {
    const { data } = await bffClient.post<BackendPayment>(`/payments/${id}/post`);
    return mapBackendPayment(data);
  },
};
