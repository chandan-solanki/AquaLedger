import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { invoiceKeys } from "@/features/invoices";
import { useCreatePaymentAllocation } from "@/features/payments/hooks/use-create-payment-allocation";

const { createPaymentAllocationMock } = vi.hoisted(() => ({
  createPaymentAllocationMock: vi.fn(),
}));

vi.mock("@/features/payments/services/payment-allocation-service", () => ({
  paymentAllocationService: { createPaymentAllocation: createPaymentAllocationMock },
}));

const CREATED_ALLOCATION = {
  id: "allocation-1",
  paymentId: "payment-1",
  invoiceId: "invoice-1",
  amount: "500.00",
};

beforeEach(() => {
  vi.clearAllMocks();
});

function renderCreateAllocation() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
  const { result } = renderHook(() => useCreatePaymentAllocation(), {
    wrapper: ({ children }) => <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>,
  });
  return { result, invalidateSpy };
}

describe("useCreatePaymentAllocation", () => {
  it("invalidates the invoice list, not just the invoice detail, since allocating recalculates status/balance shown there too", async () => {
    createPaymentAllocationMock.mockResolvedValue(CREATED_ALLOCATION);
    const { result, invalidateSpy } = renderCreateAllocation();

    act(() => {
      result.current.mutate({
        paymentId: "payment-1",
        payload: { invoice_id: "invoice-1", allocated_amount: "500.00" },
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const invalidatedKeys = invalidateSpy.mock.calls.map((call) => call[0]?.queryKey);
    expect(invalidatedKeys).toContainEqual(invoiceKeys.lists());
    expect(invalidatedKeys).toContainEqual(invoiceKeys.detail("invoice-1"));
  });
});
