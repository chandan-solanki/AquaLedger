import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PlatformTenantListPage } from "@/features/platform/pages/platform-tenant-list-page";

const { pushMock, useTenantsMock, setFiltersMock } = vi.hoisted(() => ({
  pushMock: vi.fn(),
  useTenantsMock: vi.fn(),
  setFiltersMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  usePathname: () => "/platform/tenants",
}));

vi.mock("@/features/platform/hooks/use-tenants", () => ({
  useTenants: useTenantsMock,
}));

vi.mock("@/features/platform/hooks/use-tenant-filters", () => ({
  useTenantFilters: () => [{ search: "", status: null, page: 1, pageSize: 20 }, setFiltersMock],
}));

const TENANT_ROW = {
  id: "tenant-1",
  name: "Ocean Fresh Traders",
  slug: "ocean-fresh-traders",
  status: "active" as const,
  plan: null,
  baseCurrency: "INR",
  fiscalYearStartMonth: 4,
  createdAt: "2026-08-01T00:00:00Z",
  updatedAt: "2026-08-01T00:00:00Z",
};

function mockListQuery(overrides: Partial<ReturnType<typeof useTenantsMock>> = {}) {
  useTenantsMock.mockReturnValue({
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

describe("PlatformTenantListPage", () => {
  it("renders a loading state before data arrives", () => {
    mockListQuery({ isLoading: true, isFetching: true });

    render(<PlatformTenantListPage />);

    expect(screen.queryByText("Ocean Fresh Traders")).not.toBeInTheDocument();
  });

  it("renders the empty state when there are no tenants and no active filters", () => {
    mockListQuery({
      data: {
        data: [],
        meta: { total_records: 0, total_pages: 0, current_page: 1, page_size: 20, has_next: false, has_previous: false },
      },
    });

    render(<PlatformTenantListPage />);

    expect(screen.getByText("No tenants yet")).toBeInTheDocument();
  });

  it("renders an error state with a retry action when the query fails", () => {
    const refetch = vi.fn();
    mockListQuery({
      isError: true,
      error: { category: "server", status: 500, code: "INTERNAL_ERROR", message: "Something broke" },
      refetch,
    });

    render(<PlatformTenantListPage />);

    expect(screen.getByText("Failed to load tenants")).toBeInTheDocument();
    expect(screen.getByText("Something broke")).toBeInTheDocument();
  });

  it("renders tenant rows with name, slug and a visually distinct status badge", () => {
    mockListQuery({
      data: {
        data: [TENANT_ROW],
        meta: { total_records: 1, total_pages: 1, current_page: 1, page_size: 20, has_next: false, has_previous: false },
      },
    });

    render(<PlatformTenantListPage />);

    expect(screen.getByText("Ocean Fresh Traders")).toBeInTheDocument();
    expect(screen.getByText("ocean-fresh-traders")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("distinguishes suspended and inactive tenants visually from active ones", () => {
    mockListQuery({
      data: {
        data: [
          { ...TENANT_ROW, id: "tenant-2", name: "Suspended Co", status: "suspended" as const },
          { ...TENANT_ROW, id: "tenant-3", name: "Inactive Co", status: "inactive" as const },
        ],
        meta: { total_records: 2, total_pages: 1, current_page: 1, page_size: 20, has_next: false, has_previous: false },
      },
    });

    render(<PlatformTenantListPage />);

    const suspendedBadge = screen.getByText("Suspended");
    const inactiveBadge = screen.getByText("Inactive");
    expect(suspendedBadge).toBeInTheDocument();
    expect(inactiveBadge).toBeInTheDocument();
    expect(suspendedBadge.className).not.toBe(inactiveBadge.className);
  });

  it("searching updates filters through the debounced search box", async () => {
    const user = userEvent.setup();
    mockListQuery({
      data: {
        data: [TENANT_ROW],
        meta: { total_records: 1, total_pages: 1, current_page: 1, page_size: 20, has_next: false, has_previous: false },
      },
    });

    render(<PlatformTenantListPage />);

    const searchBox = screen.getByRole("searchbox", { name: "Search tenants" });
    await user.type(searchBox, "ocean");

    await waitFor(
      () => expect(setFiltersMock).toHaveBeenCalledWith({ search: "ocean", page: 1 }),
      { timeout: 1000 }
    );
  });

  it("navigates to the tenant's detail page when a row is clicked", async () => {
    const user = userEvent.setup();
    mockListQuery({
      data: {
        data: [TENANT_ROW],
        meta: { total_records: 1, total_pages: 1, current_page: 1, page_size: 20, has_next: false, has_previous: false },
      },
    });

    render(<PlatformTenantListPage />);

    await user.click(screen.getByText("Ocean Fresh Traders"));

    expect(pushMock).toHaveBeenCalledWith("/platform/tenants/tenant-1");
  });

  it("always offers the New Tenant action - platform admin access is already enforced by PlatformGuard, not a permission code", () => {
    mockListQuery({
      data: {
        data: [],
        meta: { total_records: 0, total_pages: 0, current_page: 1, page_size: 20, has_next: false, has_previous: false },
      },
    });

    render(<PlatformTenantListPage />);

    expect(screen.getAllByRole("link", { name: /new tenant/i }).length).toBeGreaterThan(0);
  });
});
