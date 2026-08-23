import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { useAuthMock, replaceMock } = vi.hoisted(() => ({
  useAuthMock: vi.fn(),
  replaceMock: vi.fn(),
}));

vi.mock("@/features/auth/hooks/use-auth", () => ({
  useAuth: useAuthMock,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
}));

import { TenantDashboardGuard } from "@/features/dashboard/components/tenant-dashboard-guard";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("TenantDashboardGuard", () => {
  it("renders children for an ordinary tenant user, unaffected", () => {
    useAuthMock.mockReturnValue({ user: { isPlatformAdmin: false }, isLoading: false });

    render(
      <TenantDashboardGuard>
        <div>Tenant dashboard content</div>
      </TenantDashboardGuard>
    );

    expect(screen.getByText("Tenant dashboard content")).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("shows a loading indicator while the session is still resolving, never the guarded content", () => {
    useAuthMock.mockReturnValue({ user: undefined, isLoading: true });

    render(
      <TenantDashboardGuard>
        <div>Tenant dashboard content</div>
      </TenantDashboardGuard>
    );

    expect(screen.getByLabelText(/loading/i)).toBeInTheDocument();
    expect(screen.queryByText("Tenant dashboard content")).not.toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("redirects a platform admin to /platform/dashboard instead of rendering the tenant dashboard", () => {
    useAuthMock.mockReturnValue({ user: { isPlatformAdmin: true }, isLoading: false });

    render(
      <TenantDashboardGuard>
        <div>Tenant dashboard content</div>
      </TenantDashboardGuard>
    );

    expect(replaceMock).toHaveBeenCalledWith("/platform/dashboard");
    expect(screen.queryByText("Tenant dashboard content")).not.toBeInTheDocument();
  });

  it("never redirects a tenant superuser who is not a platform admin", () => {
    useAuthMock.mockReturnValue({ user: { isPlatformAdmin: false, isSuperuser: true }, isLoading: false });

    render(
      <TenantDashboardGuard>
        <div>Tenant dashboard content</div>
      </TenantDashboardGuard>
    );

    expect(replaceMock).not.toHaveBeenCalled();
    expect(screen.getByText("Tenant dashboard content")).toBeInTheDocument();
  });
});
