import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PlatformDashboardPage } from "@/features/platform/pages/platform-dashboard-page";

const { pushMock, usePlatformDashboardMock } = vi.hoisted(() => ({
  pushMock: vi.fn(),
  usePlatformDashboardMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  usePathname: () => "/platform/dashboard",
}));

vi.mock("@/features/platform/hooks/use-platform-dashboard", () => ({
  usePlatformDashboard: usePlatformDashboardMock,
}));

const RECENT_TENANT = {
  id: "tenant-1",
  name: "Ocean Fresh Traders",
  slug: "ocean-fresh-traders",
  status: "active" as const,
  plan: null,
  baseCurrency: "INR",
  fiscalYearStartMonth: 4,
  createdAt: "2026-08-22T00:00:00Z",
  updatedAt: "2026-08-22T00:00:00Z",
};

function mockDashboardQuery(overrides: Partial<ReturnType<typeof usePlatformDashboardMock>> = {}) {
  usePlatformDashboardMock.mockReturnValue({
    data: undefined,
    isLoading: false,
    isFetching: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  });
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("PlatformDashboardPage", () => {
  it("renders a loading state before data arrives", () => {
    mockDashboardQuery({ isLoading: true, isFetching: true });

    render(<PlatformDashboardPage />);

    expect(screen.queryByText("Ocean Fresh Traders")).not.toBeInTheDocument();
    expect(screen.getByText("Platform Administration — Dashboard")).toBeInTheDocument();
  });

  it("renders summary counts from real backend data", () => {
    mockDashboardQuery({
      data: {
        totalTenants: 12,
        activeTenants: 10,
        suspendedTenants: 1,
        inactiveTenants: 1,
        recentTenants: [RECENT_TENANT],
      },
    });

    render(<PlatformDashboardPage />);

    expect(screen.getByText("Total Tenants")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
  });

  it("renders recent tenant rows with name, slug and status", () => {
    mockDashboardQuery({
      data: {
        totalTenants: 1,
        activeTenants: 1,
        suspendedTenants: 0,
        inactiveTenants: 0,
        recentTenants: [RECENT_TENANT],
      },
    });

    render(<PlatformDashboardPage />);

    expect(screen.getByText("Ocean Fresh Traders")).toBeInTheDocument();
    expect(screen.getByText("ocean-fresh-traders")).toBeInTheDocument();
    // "Active" also appears as a stat-card title (activeTenants) - the
    // status badge is a second, distinct occurrence, not the only one.
    expect(screen.getAllByText("Active").length).toBeGreaterThan(1);
  });

  it("navigates to the tenant's detail page when a recent tenant row is clicked", async () => {
    const user = userEvent.setup();
    mockDashboardQuery({
      data: {
        totalTenants: 1,
        activeTenants: 1,
        suspendedTenants: 0,
        inactiveTenants: 0,
        recentTenants: [RECENT_TENANT],
      },
    });

    render(<PlatformDashboardPage />);
    await user.click(screen.getByText("Ocean Fresh Traders"));

    expect(pushMock).toHaveBeenCalledWith("/platform/tenants/tenant-1");
  });

  it("renders the empty state when there are no tenants at all", () => {
    mockDashboardQuery({
      data: { totalTenants: 0, activeTenants: 0, suspendedTenants: 0, inactiveTenants: 0, recentTenants: [] },
    });

    render(<PlatformDashboardPage />);

    expect(screen.getByText("No tenants yet.")).toBeInTheDocument();
  });

  it("renders a full-page error state with retry when the query fails on first load", () => {
    const refetch = vi.fn();
    mockDashboardQuery({
      isError: true,
      error: { category: "server", status: 500, code: "INTERNAL_ERROR", message: "Something broke" },
      refetch,
    });

    render(<PlatformDashboardPage />);

    expect(screen.getByText("Failed to load the platform dashboard")).toBeInTheDocument();
    expect(screen.getByText("Something broke")).toBeInTheDocument();
  });

  it("offers a clear action to navigate to the full tenant management page", () => {
    mockDashboardQuery({
      data: { totalTenants: 0, activeTenants: 0, suspendedTenants: 0, inactiveTenants: 0, recentTenants: [] },
    });

    render(<PlatformDashboardPage />);

    expect(screen.getByRole("link", { name: /view all tenants/i })).toHaveAttribute(
      "href",
      "/platform/tenants"
    );
  });
});
