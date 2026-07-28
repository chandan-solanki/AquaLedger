import { bffClient } from "@/lib/bff-client";
import type {
  BackendSupplierPaymentAllocation,
  SupplierPaymentAllocation,
  SupplierPaymentAllocationCreateRequest,
  SupplierPaymentAllocationUpdateRequest,
} from "@/features/supplier-payments/types/supplier-payment-allocation";
import { mapBackendSupplierPaymentAllocation } from "@/features/supplier-payments/types/supplier-payment-allocation";

/**
 * Talks only to the Next.js BFF's own routes
 * (`/api/supplier-payments/{id}/allocations*`) - never the FastAPI backend
 * directly, mirroring `payment-allocation-service.ts`. The BFF route
 * handlers attach the caller's HttpOnly access token server-side and
 * forward the request. `listSupplierPaymentAllocations` returns a plain
 * array, not a paginated envelope - the backend itself returns
 * `list[SupplierPaymentAllocationResponse]`, not `PaginatedResponse[...]`
 * (app/modules/supplier_payments/router.py: "a payment's allocation count
 * is small and bounded").
 */
export const supplierPaymentAllocationService = {
  async listSupplierPaymentAllocations(
    supplierPaymentId: string
  ): Promise<SupplierPaymentAllocation[]> {
    const { data } = await bffClient.get<BackendSupplierPaymentAllocation[]>(
      `/supplier-payments/${supplierPaymentId}/allocations`
    );
    return data.map(mapBackendSupplierPaymentAllocation);
  },

  async createSupplierPaymentAllocation(
    supplierPaymentId: string,
    payload: SupplierPaymentAllocationCreateRequest
  ): Promise<SupplierPaymentAllocation> {
    const { data } = await bffClient.post<BackendSupplierPaymentAllocation>(
      `/supplier-payments/${supplierPaymentId}/allocations`,
      payload
    );
    return mapBackendSupplierPaymentAllocation(data);
  },

  async updateSupplierPaymentAllocation(
    supplierPaymentId: string,
    allocationId: string,
    payload: SupplierPaymentAllocationUpdateRequest
  ): Promise<SupplierPaymentAllocation> {
    const { data } = await bffClient.put<BackendSupplierPaymentAllocation>(
      `/supplier-payments/${supplierPaymentId}/allocations/${allocationId}`,
      payload
    );
    return mapBackendSupplierPaymentAllocation(data);
  },

  async deleteSupplierPaymentAllocation(
    supplierPaymentId: string,
    allocationId: string
  ): Promise<void> {
    await bffClient.delete(`/supplier-payments/${supplierPaymentId}/allocations/${allocationId}`);
  },
};
