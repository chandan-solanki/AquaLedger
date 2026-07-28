import { bffClient } from "@/lib/bff-client";
import type {
  BackendPaymentAllocation,
  PaymentAllocation,
  PaymentAllocationCreateRequest,
  PaymentAllocationUpdateRequest,
} from "@/features/payments/types/payment-allocation";
import { mapBackendPaymentAllocation } from "@/features/payments/types/payment-allocation";

/**
 * Talks only to the Next.js BFF's own routes (`/api/payments/{id}/allocations*`)
 * - never the FastAPI backend directly, mirroring `invoice-item-service.ts`.
 * The BFF route handlers attach the caller's HttpOnly access token server-
 * side and forward the request. `listPaymentAllocations` returns a plain
 * array, not a paginated envelope - the backend itself returns
 * `list[PaymentAllocationResponse]`, not `PaginatedResponse[...]`
 * (app/modules/payments/router.py: "a payment's allocation count is small
 * and bounded").
 */
export const paymentAllocationService = {
  async listPaymentAllocations(paymentId: string): Promise<PaymentAllocation[]> {
    const { data } = await bffClient.get<BackendPaymentAllocation[]>(
      `/payments/${paymentId}/allocations`
    );
    return data.map(mapBackendPaymentAllocation);
  },

  async createPaymentAllocation(
    paymentId: string,
    payload: PaymentAllocationCreateRequest
  ): Promise<PaymentAllocation> {
    const { data } = await bffClient.post<BackendPaymentAllocation>(
      `/payments/${paymentId}/allocations`,
      payload
    );
    return mapBackendPaymentAllocation(data);
  },

  async updatePaymentAllocation(
    paymentId: string,
    allocationId: string,
    payload: PaymentAllocationUpdateRequest
  ): Promise<PaymentAllocation> {
    const { data } = await bffClient.put<BackendPaymentAllocation>(
      `/payments/${paymentId}/allocations/${allocationId}`,
      payload
    );
    return mapBackendPaymentAllocation(data);
  },

  async deletePaymentAllocation(paymentId: string, allocationId: string): Promise<void> {
    await bffClient.delete(`/payments/${paymentId}/allocations/${allocationId}`);
  },
};
