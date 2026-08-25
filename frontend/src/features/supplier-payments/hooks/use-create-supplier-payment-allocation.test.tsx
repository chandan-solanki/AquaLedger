import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { purchaseBillKeys } from "@/features/purchase-bills";
import { useCreateSupplierPaymentAllocation } from "@/features/supplier-payments/hooks/use-create-supplier-payment-allocation";

const { createSupplierPaymentAllocationMock } = vi.hoisted(() => ({
  createSupplierPaymentAllocationMock: vi.fn(),
}));

vi.mock("@/features/supplier-payments/services/supplier-payment-allocation-service", () => ({
  supplierPaymentAllocationService: {
    createSupplierPaymentAllocation: createSupplierPaymentAllocationMock,
  },
}));

const CREATED_ALLOCATION = {
  id: "allocation-1",
  supplierPaymentId: "supplier-payment-1",
  purchaseBillId: "bill-1",
  allocatedAmount: "500.00",
};

beforeEach(() => {
  vi.clearAllMocks();
});

function renderCreateAllocation() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
  const { result } = renderHook(() => useCreateSupplierPaymentAllocation(), {
    wrapper: ({ children }) => <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>,
  });
  return { result, invalidateSpy };
}

describe("useCreateSupplierPaymentAllocation", () => {
  it("invalidates the purchase bill list, not just the bill detail, since allocating recalculates status/balance shown there too", async () => {
    createSupplierPaymentAllocationMock.mockResolvedValue(CREATED_ALLOCATION);
    const { result, invalidateSpy } = renderCreateAllocation();

    act(() => {
      result.current.mutate({
        supplierPaymentId: "supplier-payment-1",
        payload: { purchase_bill_id: "bill-1", allocated_amount: "500.00" },
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const invalidatedKeys = invalidateSpy.mock.calls.map((call) => call[0]?.queryKey);
    expect(invalidatedKeys).toContainEqual(purchaseBillKeys.lists());
    expect(invalidatedKeys).toContainEqual(purchaseBillKeys.detail("bill-1"));
  });
});
