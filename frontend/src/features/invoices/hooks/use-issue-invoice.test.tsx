import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useIssueInvoice } from "@/features/invoices/hooks/use-issue-invoice";

const { issueInvoiceMock } = vi.hoisted(() => ({
  issueInvoiceMock: vi.fn(),
}));

vi.mock("@/features/invoices/services/invoice-service", () => ({
  invoiceService: { issueInvoice: issueInvoiceMock },
}));

vi.mock("@/lib/toast", () => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}));

const ISSUED_INVOICE = {
  id: "invoice-1",
  companyId: "company-1",
  invoiceNumber: "INV-0001",
};

beforeEach(() => {
  vi.clearAllMocks();
});

function renderIssueInvoice() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
  const { result } = renderHook(() => useIssueInvoice(), {
    wrapper: ({ children }) => <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>,
  });
  return { result, invalidateSpy };
}

describe("useIssueInvoice", () => {
  it("invalidates Fish Stock queries on a successful issue (Sprint 15 Session 11 regression)", async () => {
    issueInvoiceMock.mockResolvedValue(ISSUED_INVOICE);
    const { result, invalidateSpy } = renderIssueInvoice();

    act(() => {
      result.current.mutate("invoice-1");
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const invalidatedKeys = invalidateSpy.mock.calls.map((call) => call[0]?.queryKey);
    expect(invalidatedKeys).toContainEqual(["fish-stock"]);
    expect(invalidatedKeys).toContainEqual(["trip-catches"]);
  });
});
