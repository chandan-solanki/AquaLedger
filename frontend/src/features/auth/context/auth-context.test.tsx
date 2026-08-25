import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiError } from "@/types/api";

const { getSessionMock, replaceMock, pushMock } = vi.hoisted(() => ({
  getSessionMock: vi.fn(),
  replaceMock: vi.fn(),
  pushMock: vi.fn(),
}));

vi.mock("@/features/auth/services/auth-service", () => ({
  authService: {
    getSession: getSessionMock,
    login: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
  },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock, push: pushMock }),
  usePathname: () => "/dashboard",
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

import { AuthProvider } from "@/features/auth/context/auth-context";

const UNAUTHORIZED_ERROR: ApiError = {
  category: "unauthorized",
  status: 401,
  code: "NO_SESSION",
  message: "No active session.",
};

function renderProvider(queryClient: QueryClient) {
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <div>content</div>
      </AuthProvider>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AuthProvider session-query cache hygiene", () => {
  it("clears the entire query cache once the session query itself resolves to unauthenticated", async () => {
    getSessionMock.mockRejectedValue(UNAUTHORIZED_ERROR);

    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    // Simulates a previous (possibly different) user's cached tenant data
    // still sitting in this in-memory QueryClient — e.g. a shared/kiosk
    // device where the prior session expired naturally.
    queryClient.setQueryData(["dashboard", "summary"], { totalRevenue: 999 });

    renderProvider(queryClient);

    await waitFor(() => {
      expect(queryClient.getQueryData(["dashboard", "summary"])).toBeUndefined();
    });

    // This is silent housekeeping, not a user-facing "session expired"
    // event — a fresh anonymous visitor must never see that toast/redirect.
    expect(replaceMock).not.toHaveBeenCalled();
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("does not clear the cache while the session resolves successfully", async () => {
    getSessionMock.mockResolvedValue({
      user: { id: "u1", tenantId: "t1", permissions: [] },
    });

    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    queryClient.setQueryData(["dashboard", "summary"], { totalRevenue: 999 });

    renderProvider(queryClient);

    await waitFor(() => {
      expect(getSessionMock).toHaveBeenCalled();
    });

    expect(queryClient.getQueryData(["dashboard", "summary"])).toEqual({ totalRevenue: 999 });
  });
});
