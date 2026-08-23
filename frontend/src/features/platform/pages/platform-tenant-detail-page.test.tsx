import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { TenantStatus } from "@/features/platform/types/tenant";

const { useTenantMock, useUpdateTenantStatusMock, updateTenantStatusMutateMock } = vi.hoisted(() => ({
  useTenantMock: vi.fn(),
  useUpdateTenantStatusMock: vi.fn(),
  updateTenantStatusMutateMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "tenant-1" }),
  usePathname: () => "/platform/tenants/tenant-1",
}));

vi.mock("@/features/platform/hooks/use-tenant", () => ({
  useTenant: useTenantMock,
}));

vi.mock("@/features/platform/hooks/use-update-tenant-status", () => ({
  useUpdateTenantStatus: useUpdateTenantStatusMock,
}));

import { PlatformTenantDetailPage } from "@/features/platform/pages/platform-tenant-detail-page";

const ACTIVE_TENANT = {
  id: "tenant-1",
  name: "Ocean Fresh Traders",
  slug: "ocean-fresh-traders",
  status: "active" as TenantStatus,
  plan: null,
  baseCurrency: "INR",
  fiscalYearStartMonth: 4,
  createdAt: "2026-08-01T00:00:00Z",
  updatedAt: "2026-08-01T00:00:00Z",
};

function mockTenant(overrides: Partial<typeof ACTIVE_TENANT> = {}) {
  useTenantMock.mockReturnValue({
    data: { ...ACTIVE_TENANT, ...overrides },
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  mockTenant();
  useUpdateTenantStatusMock.mockReturnValue({ mutate: updateTenantStatusMutateMock, isPending: false });
});

describe("PlatformTenantDetailPage", () => {
  it("renders tenant metadata", () => {
    render(<PlatformTenantDetailPage />);

    expect(screen.getAllByText("Ocean Fresh Traders").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Active").length).toBeGreaterThan(0);
    expect(screen.getByText("INR")).toBeInTheDocument();
  });

  it("offers Suspend and Deactivate for an active tenant, not Reactivate", () => {
    render(<PlatformTenantDetailPage />);

    expect(screen.getByRole("button", { name: /suspend/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /deactivate/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /reactivate/i })).not.toBeInTheDocument();
  });

  it("offers only Reactivate for a suspended tenant", () => {
    mockTenant({ status: "suspended" });
    render(<PlatformTenantDetailPage />);

    expect(screen.getByRole("button", { name: /reactivate/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /suspend/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^deactivate$/i })).not.toBeInTheDocument();
  });

  it("offers only Reactivate for an inactive tenant", () => {
    mockTenant({ status: "inactive" });
    render(<PlatformTenantDetailPage />);

    expect(screen.getByRole("button", { name: /reactivate/i })).toBeInTheDocument();
  });

  it("requires confirmation before suspending, and cancel makes no API call", async () => {
    const user = userEvent.setup();
    render(<PlatformTenantDetailPage />);

    await user.click(screen.getByRole("button", { name: /suspend/i }));
    const dialog = screen.getByRole("alertdialog");
    expect(within(dialog).getByText(/blocked immediately/i)).toBeInTheDocument();

    await user.click(within(dialog).getByRole("button", { name: /cancel/i }));

    expect(updateTenantStatusMutateMock).not.toHaveBeenCalled();
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("sends the correct status payload when suspension is confirmed", async () => {
    const user = userEvent.setup();
    render(<PlatformTenantDetailPage />);

    await user.click(screen.getByRole("button", { name: /suspend/i }));
    const dialog = screen.getByRole("alertdialog");
    await user.click(within(dialog).getByRole("button", { name: /^suspend$/i }));

    expect(updateTenantStatusMutateMock).toHaveBeenCalledWith(
      { id: "tenant-1", status: "suspended" },
      expect.objectContaining({ onSuccess: expect.any(Function) })
    );
  });

  it("sends the correct status payload when deactivation is confirmed", async () => {
    const user = userEvent.setup();
    render(<PlatformTenantDetailPage />);

    await user.click(screen.getByRole("button", { name: /deactivate/i }));
    const dialog = screen.getByRole("alertdialog");
    await user.click(within(dialog).getByRole("button", { name: /^deactivate$/i }));

    expect(updateTenantStatusMutateMock).toHaveBeenCalledWith(
      { id: "tenant-1", status: "inactive" },
      expect.objectContaining({ onSuccess: expect.any(Function) })
    );
  });

  it("sends the correct status payload when reactivation is confirmed", async () => {
    mockTenant({ status: "suspended" });
    const user = userEvent.setup();
    render(<PlatformTenantDetailPage />);

    await user.click(screen.getByRole("button", { name: /reactivate/i }));
    const dialog = screen.getByRole("alertdialog");
    await user.click(within(dialog).getByRole("button", { name: /^reactivate$/i }));

    expect(updateTenantStatusMutateMock).toHaveBeenCalledWith(
      { id: "tenant-1", status: "active" },
      expect.objectContaining({ onSuccess: expect.any(Function) })
    );
  });

  it("disables the confirm action while the mutation is pending, preventing a duplicate submission", async () => {
    useUpdateTenantStatusMock.mockReturnValue({ mutate: updateTenantStatusMutateMock, isPending: true });
    const user = userEvent.setup();
    render(<PlatformTenantDetailPage />);

    await user.click(screen.getByRole("button", { name: /suspend/i }));
    const dialog = screen.getByRole("alertdialog");

    expect(within(dialog).getByRole("button", { name: /^suspend$/i })).toBeDisabled();
  });

  it("renders a loading state while the tenant is loading", () => {
    useTenantMock.mockReturnValue({ data: undefined, isLoading: true, isError: false, error: null, refetch: vi.fn() });

    render(<PlatformTenantDetailPage />);

    expect(screen.queryByText("Ocean Fresh Traders")).not.toBeInTheDocument();
  });

  it("renders an error state with retry when the tenant fails to load", () => {
    const refetch = vi.fn();
    useTenantMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: { category: "not_found", status: 404, code: "TENANT_NOT_FOUND", message: "Tenant not found" },
      refetch,
    });

    render(<PlatformTenantDetailPage />);

    expect(screen.getByText("Failed to load tenant")).toBeInTheDocument();
    expect(screen.getByText("Tenant not found")).toBeInTheDocument();
  });
});
