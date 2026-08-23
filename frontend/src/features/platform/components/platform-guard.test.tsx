import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { useAuthMock } = vi.hoisted(() => ({
  useAuthMock: vi.fn(),
}));

vi.mock("@/features/auth/hooks/use-auth", () => ({
  useAuth: useAuthMock,
}));

import { PlatformGuard } from "@/features/platform/components/platform-guard";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("PlatformGuard", () => {
  it("renders children for a platform admin", () => {
    useAuthMock.mockReturnValue({ user: { isPlatformAdmin: true }, isLoading: false });

    render(
      <PlatformGuard>
        <div>Platform content</div>
      </PlatformGuard>
    );

    expect(screen.getByText("Platform content")).toBeInTheDocument();
  });

  it("shows a loading indicator while the session is still resolving, never the guarded content or the denial message", () => {
    useAuthMock.mockReturnValue({ user: undefined, isLoading: true });

    render(
      <PlatformGuard>
        <div>Platform content</div>
      </PlatformGuard>
    );

    expect(screen.getByLabelText(/loading/i)).toBeInTheDocument();
    expect(screen.queryByText("Platform content")).not.toBeInTheDocument();
    expect(screen.queryByText(/don't have access/i)).not.toBeInTheDocument();
  });

  it("denies an authenticated non-platform-admin user with an inline error, not the guarded content", () => {
    useAuthMock.mockReturnValue({ user: { isPlatformAdmin: false }, isLoading: false });

    render(
      <PlatformGuard>
        <div>Platform content</div>
      </PlatformGuard>
    );

    expect(screen.getByText(/don't have access to platform administration/i)).toBeInTheDocument();
    expect(screen.queryByText("Platform content")).not.toBeInTheDocument();
  });

  it("denies a tenant superuser who is not a platform admin - isSuperuser never substitutes for isPlatformAdmin", () => {
    useAuthMock.mockReturnValue({
      user: { isPlatformAdmin: false, isSuperuser: true },
      isLoading: false,
    });

    render(
      <PlatformGuard>
        <div>Platform content</div>
      </PlatformGuard>
    );

    expect(screen.getByText(/don't have access to platform administration/i)).toBeInTheDocument();
    expect(screen.queryByText("Platform content")).not.toBeInTheDocument();
  });

  it("denies when there is no user at all (defensive: should never happen inside AuthGuard)", () => {
    useAuthMock.mockReturnValue({ user: null, isLoading: false });

    render(
      <PlatformGuard>
        <div>Platform content</div>
      </PlatformGuard>
    );

    expect(screen.getByText(/don't have access to platform administration/i)).toBeInTheDocument();
  });
});
